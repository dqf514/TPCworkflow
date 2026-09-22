# -*- coding: utf-8 -*-
"""轻量工作流引擎：条件分支、或签/会签/依次、抄送、选项校验。"""
import json
from datetime import datetime

from flask import current_app

from app.extensions import db
from app.models import (
    InstanceTimeline,
    TaskInstance,
    User,
    WorkflowDefinition,
    WorkflowInstance,
)
from app.services.apply_visibility import user_can_apply_workflow
from app.services.assignee_resolver import AssigneeResolver
from app.services.graph_utils import (
    find_node,
    parse_graph,
    parse_variables,
    resolve_next_node_ids,
)
from app.services.workflow_settings import merge_settings
from app.services.notify import notify_instance_result_if_finished, notify_pending_tasks
from app.services.instance_access import ensure_instance_public_uuid
from app.services.instance_number import allocate_workflow_display_no
from app.services.workflow_add_sign import (
    all_add_sign_siblings_done,
    cancel_other_or_sign_tasks,
    is_add_sign_task,
    normalize_target_user_ids_for_node,
    notify_task_ids,
    parse_task_meta,
    release_parent_after_before_sign,
    start_after_add_sign,
    start_before_add_sign,
)
from app.services.workflow_task_utils import (
    append_auto_approve_timeline,
    create_auto_approved_task,
    resolve_assignees_for_node,
    should_auto_approve_duplicate,
)


class WorkflowEngine:
    def start(
        self,
        definition: WorkflowDefinition,
        initiator_id: int,
        company_id: int,
        department_id: int | None = None,
        org_unit_id: int | None = None,
        variables: dict | None = None,
        business_type: str | None = None,
        business_id: str | None = None,
    ) -> WorkflowInstance:
        user = User.query.get(initiator_id)
        if not user or not user_can_apply_workflow(user, definition, company_id):
            raise ValueError('无权在该公司下发起该流程，或您不在该流程的发起可见范围内')

        graph = parse_graph(definition.process_graph)
        start_node = find_node(graph, 'start')
        if not start_node:
            raise ValueError('流程图缺少开始节点')

        vars_payload = variables or {}
        vars_payload.setdefault('org', {})
        vars_payload['org'].update({
            'company_id': company_id,
            'department_id': department_id,
            'org_unit_id': org_unit_id,
            'initiator_id': initiator_id,
        })

        inst = WorkflowInstance(
            definition_id=definition.id,
            initiator_id=initiator_id,
            company_id=company_id,
            department_id=department_id,
            org_unit_id=org_unit_id,
            business_sector_id=definition.business_sector_id,
            business_type=business_type,
            business_id=business_id,
            status='running',
            variables=json.dumps(vars_payload, ensure_ascii=False),
            current_node_ids=json.dumps([]),
        )
        db.session.add(inst)
        db.session.flush()
        inst.display_no = allocate_workflow_display_no()
        ensure_instance_public_uuid(inst)

        self._append_timeline(inst.id, initiator_id, 'submit', start_node.get('id'), '已提交')
        next_ids = resolve_next_node_ids(graph, start_node.get('id'), vars_payload)
        if not next_ids:
            next_ids = _next_from_start_legacy(graph, start_node)
        notify_ids = self._advance(inst, graph, next_ids, definition)
        db.session.commit()
        app = current_app._get_current_object()
        notify_instance_result_if_finished(app, inst)
        if notify_ids:
            notify_pending_tasks(app, notify_ids)
        return inst

    def complete_task(
        self,
        task: TaskInstance,
        action: str,
        actor_id: int,
        comment: str | None = None,
        action_meta: dict | None = None,
        form_update: dict | None = None,
    ) -> WorkflowInstance:
        if task.status not in ('pending',):
            raise ValueError('任务已处理')
        if task.assignee_id != actor_id:
            raise ValueError('无权处理该任务')

        inst = task.instance
        definition = inst.definition
        graph = parse_graph(definition.process_graph)
        settings = merge_settings(definition.settings)
        variables = parse_variables(inst.variables)
        meta_in = action_meta or {}
        task_meta = parse_task_meta(task)
        original_form = dict(variables.get('form') or {})

        if is_add_sign_task(task_meta) and action in ('add_sign', 'transfer'):
            raise ValueError('加签任务不支持该操作')

        if action == 'add_sign' or meta_in.get('add_sign_mode') == 'before':
            if action != 'add_sign':
                raise ValueError('前加签请使用加签操作')
            return self._do_add_sign_before(
                task, actor_id, comment, meta_in, settings, inst, graph, definition,
            )

        if is_add_sign_task(task_meta):
            return self._complete_add_sign_task(
                task,
                action,
                actor_id,
                comment,
                meta_in,
                settings,
                form_update,
                inst,
                graph,
                definition,
                variables,
            )

        if form_update and action == 'approve':
            merged = dict(original_form)
            merged.update(form_update)
            variables['form'] = merged
            inst.variables = json.dumps(variables, ensure_ascii=False)

        if action == 'approve':
            from app.services.form_schema import resolve_definition_schema
            from app.services.node_field_requirements import validate_node_field_requirements

            node = find_node(graph, task.node_id) or {}
            node_config = node.get('config') or {}
            schema = resolve_definition_schema(definition)
            current_form = dict(variables.get('form') or {})
            node_errs = validate_node_field_requirements(
                schema,
                current_form,
                node_config,
                original_form=original_form,
            )
            if node_errs:
                raise ValueError('；'.join(node_errs))

        self._validate_approval_comment(action, task, settings, comment, meta_in)

        after_targets: list[int] = []
        if action == 'approve' and meta_in.get('add_sign_mode') == 'after' and meta_in.get('target_user_ids'):
            if not settings.get('allow_add_sign'):
                raise ValueError('该流程未开启加签')
            after_targets = normalize_target_user_ids_for_node(
                actor_id, meta_in.get('target_user_ids') or [], inst, task.node_id,
            )

        if action == 'transfer':
            if not settings.get('allow_transfer'):
                raise ValueError('该流程未开启转交')
            if task_meta.get('add_sign_hold'):
                raise ValueError('前加签等待中，不可转交')

        task.status = (
            'approved'
            if action == 'approve'
            else 'rejected'
            if action == 'reject'
            else action
        )
        task.completed_at = datetime.now()
        stored_meta = dict(meta_in) if meta_in else {}
        if stored_meta:
            task.action_meta = json.dumps(stored_meta, ensure_ascii=False)

        self._append_timeline(
            inst.id,
            actor_id,
            action,
            task.node_id,
            comment or '',
            payload=meta_in,
        )

        notify_ids: list[int] = []

        if action == 'transfer':
            new_uid = (action_meta or {}).get('target_user_id')
            if not new_uid:
                raise ValueError('请选择转交对象')
            db.session.add(
                TaskInstance(
                    instance_id=inst.id,
                    node_id=task.node_id,
                    node_type=task.node_type,
                    assignee_id=int(new_uid),
                    status='pending',
                ),
            )
            db.session.flush()
            new_task = inst.tasks.filter_by(
                node_id=task.node_id,
                assignee_id=int(new_uid),
                status='pending',
            ).order_by(TaskInstance.id.desc()).first()
            new_task_id = new_task.id if new_task else None
            db.session.commit()
            if new_task_id:
                notify_pending_tasks(current_app._get_current_object(), [new_task_id])
            return inst

        if action != 'approve':
            inst.status = 'rejected' if action == 'reject' else action
            inst.finished_at = datetime.now()
            inst.current_node_ids = json.dumps([])
            db.session.commit()
            notify_instance_result_if_finished(current_app._get_current_object(), inst)
            return inst

        if after_targets:
            notify_ids.extend(
                start_after_add_sign(
                    task,
                    actor_id,
                    after_targets,
                    comment or '',
                    self._append_timeline,
                    graph=graph,
                ),
            )

        notify_ids.extend(self._continue_after_task_approved(task, inst, graph, definition, variables))
        db.session.commit()
        app = current_app._get_current_object()
        notify_instance_result_if_finished(app, inst)
        notify_task_ids(app, notify_ids)
        return inst

    def _validate_approval_comment(
        self,
        action: str,
        task: TaskInstance,
        settings: dict,
        comment: str | None,
        action_meta: dict,
    ) -> None:
        if action in ('approve', 'reject') and settings.get('require_comment'):
            if not (comment or '').strip():
                raise ValueError('请填写审批意见')
        if action == 'approve' and settings.get('require_handwritten_sign'):
            if not action_meta.get('signature_path') and not action_meta.get('signature_data'):
                raise ValueError('请完成手写签名')
        if action == 'approve' and task.node_type == 'handler':
            if settings.get('require_handler_comment') and not (comment or '').strip():
                raise ValueError('请填写办理意见')

    def _do_add_sign_before(
        self,
        task: TaskInstance,
        actor_id: int,
        comment: str | None,
        action_meta: dict,
        settings: dict,
        inst: WorkflowInstance,
        graph: dict,
        definition: WorkflowDefinition,
    ) -> WorkflowInstance:
        if not settings.get('allow_add_sign'):
            raise ValueError('该流程未开启加签')
        if task.node_type not in ('approver', 'handler'):
            raise ValueError('当前节点不支持加签')
        targets = normalize_target_user_ids_for_node(
            actor_id,
            action_meta.get('target_user_ids') or [],
            inst,
            task.node_id,
        )
        notify_ids = start_before_add_sign(
            task,
            actor_id,
            targets,
            comment or '',
            self._append_timeline,
        )
        db.session.commit()
        notify_task_ids(current_app._get_current_object(), notify_ids)
        return inst

    def _complete_add_sign_task(
        self,
        task: TaskInstance,
        action: str,
        actor_id: int,
        comment: str | None,
        action_meta: dict,
        settings: dict,
        form_update: dict | None,
        inst: WorkflowInstance,
        graph: dict,
        definition: WorkflowDefinition,
        variables: dict,
    ) -> WorkflowInstance:
        if action not in ('approve', 'reject'):
            raise ValueError('加签任务仅支持同意或驳回')
        self._validate_approval_comment(action, task, settings, comment, action_meta)

        task_meta = parse_task_meta(task)
        mode = task_meta.get('add_sign_mode') or 'before'
        parent_id = int(task_meta.get('parent_task_id') or 0)
        parent = TaskInstance.query.get(parent_id) if parent_id else None

        task.status = 'approved' if action == 'approve' else 'rejected'
        task.completed_at = datetime.now()
        if action_meta:
            merged = {**task_meta, **action_meta}
            task.action_meta = json.dumps(merged, ensure_ascii=False)

        self._append_timeline(
            inst.id,
            actor_id,
            action,
            task.node_id,
            comment or ('加签同意' if action == 'approve' else '加签驳回'),
            payload=action_meta,
        )

        notify_ids: list[int] = []

        if action == 'reject':
            inst.status = 'rejected'
            inst.finished_at = datetime.now()
            inst.current_node_ids = json.dumps([])
            for t in inst.tasks.filter_by(status='pending').all():
                t.status = 'cancelled'
                t.completed_at = datetime.now()
            db.session.commit()
            notify_instance_result_if_finished(current_app._get_current_object(), inst)
            return inst

        if not all_add_sign_siblings_done(parent_id, mode):
            db.session.commit()
            return inst

        if mode == 'before' and parent and parent.status == 'on_hold':
            release_parent_after_before_sign(parent)
            db.session.flush()
            notify_ids.append(parent.id)

        if mode == 'after' and parent and parent.status == 'approved':
            notify_ids.extend(
                self._continue_after_task_approved(parent, inst, graph, definition, variables),
            )

        db.session.commit()
        app = current_app._get_current_object()
        notify_instance_result_if_finished(app, inst)
        notify_task_ids(app, notify_ids)
        return inst

    def _continue_after_task_approved(
        self,
        task: TaskInstance,
        inst: WorkflowInstance,
        graph: dict,
        definition: WorkflowDefinition,
        variables: dict,
    ) -> list[int]:
        notify_ids: list[int] = []
        seq_id = self._spawn_next_sequential_task(inst, task)
        if seq_id:
            notify_ids.append(seq_id)

        node = find_node(graph, task.node_id)
        cancel_other_or_sign_tasks(inst, graph, task.node_id, task.id)
        if not self._node_approved(graph, node, inst, task.node_id):
            return notify_ids

        try:
            from app.services.notify import notify_node_extra_emails_on_complete

            notify_node_extra_emails_on_complete(
                current_app._get_current_object(),
                inst.id,
                task.node_id,
                task.id,
            )
        except Exception:
            pass

        next_ids = resolve_next_node_ids(graph, task.node_id, variables)
        if not next_ids:
            next_ids = (node or {}).get('next') or []
        if not next_ids:
            inst.status = 'approved'
            inst.finished_at = datetime.now()
            inst.current_node_ids = json.dumps([])
        else:
            notify_ids.extend(self._advance(inst, graph, next_ids, definition))
        return notify_ids

    def _node_approved(self, graph: dict, node: dict | None, inst: WorkflowInstance, node_id: str) -> bool:
        if not node:
            return True
        apv_rel = (node.get('config') or {}).get('apv_rel') or node.get('apv_rel') or 'or'
        pending = inst.tasks.filter_by(node_id=node_id, status='pending').count()
        if pending > 0:
            return False
        if apv_rel == 'and':
            rejected = inst.tasks.filter(
                TaskInstance.node_id == node_id,
                TaskInstance.status.in_(['reject', 'rejected']),
            ).count()
            if rejected:
                return False
            approved = inst.tasks.filter_by(node_id=node_id, status='approved').count()
            resolver = AssigneeResolver(inst)
            needed = len(resolver.resolve(node.get('config') or {}))
            return approved >= needed and needed > 0
        return True

    def _advance(
        self,
        inst: WorkflowInstance,
        graph: dict,
        node_ids: list,
        definition: WorkflowDefinition,
    ) -> list[int]:
        notify_ids: list[int] = []
        if not node_ids:
            return notify_ids
        inst.current_node_ids = json.dumps(node_ids)
        resolver = AssigneeResolver(inst)
        variables = parse_variables(inst.variables)
        settings = merge_settings(definition.settings)

        for nid in node_ids:
            node = find_node(graph, nid)
            if not node:
                continue
            ntype = node.get('type')

            if ntype == 'end':
                inst.status = 'approved'
                inst.finished_at = datetime.now()
                inst.current_node_ids = json.dumps([])
                return notify_ids

            if ntype == 'condition':
                targets = resolve_next_node_ids(graph, nid, variables)
                if not targets:
                    # 无命中分支且无默认出口：视为审批完成，避免卡在「条件分支」
                    inst.status = 'approved'
                    inst.finished_at = datetime.now()
                    inst.current_node_ids = json.dumps([])
                    return notify_ids
                notify_ids.extend(self._advance(inst, graph, targets, definition))
                if inst.status == 'running' and not inst.tasks.filter_by(status='pending').first():
                    inst.status = 'approved'
                    inst.finished_at = inst.finished_at or datetime.now()
                    inst.current_node_ids = json.dumps([])
                return notify_ids

            if ntype == 'parallel':
                branches = node.get('branches') or get_parallel_branch_targets(graph, nid)
                for branch_targets in branches:
                    if isinstance(branch_targets, str):
                        notify_ids.extend(self._advance(inst, graph, [branch_targets], definition))
                    elif isinstance(branch_targets, list):
                        notify_ids.extend(self._advance(inst, graph, branch_targets, definition))
                return notify_ids

            if ntype == 'cc':
                for uid in resolver.resolve(node.get('config') or {}):
                    self._append_timeline(
                        inst.id,
                        uid,
                        'cc',
                        nid,
                        '抄送',
                    )
                next_ids = resolve_next_node_ids(graph, nid, variables)
                if not next_ids:
                    next_ids = (node.get('next') or [])
                notify_ids.extend(self._advance(inst, graph, next_ids, definition))
                continue

            if ntype in ('approver', 'handler'):
                config = node.get('config') or {}
                apv_rel = config.get('apv_rel') or node.get('apv_rel') or 'or'
                assignees, auto_skip, skip_reason = resolve_assignees_for_node(
                    inst, config, settings, ntype,
                )
                if auto_skip and not assignees:
                    append_auto_approve_timeline(
                        inst.id,
                        nid,
                        skip_reason or '审批人为空，已按设置自动同意',
                    )
                    next_ids = resolve_next_node_ids(graph, nid, variables)
                    if not next_ids:
                        next_ids = (node.get('next') or [])
                    notify_ids.extend(self._advance(inst, graph, next_ids, definition))
                    return notify_ids

                if not assignees:
                    raise ValueError(f'节点 {nid} 未解析到审批人，请在流程设置中配置异常处理')

                pending_assignees = []
                for uid in assignees:
                    if should_auto_approve_duplicate(inst, settings, uid):
                        create_auto_approved_task(
                            inst, nid, ntype, uid, '同一审批人在本单重复出现，已自动同意',
                        )
                    else:
                        pending_assignees.append(uid)

                if not pending_assignees:
                    if self._node_approved(graph, node, inst, nid):
                        next_ids = resolve_next_node_ids(graph, nid, variables)
                        if not next_ids:
                            next_ids = (node.get('next') or [])
                        notify_ids.extend(self._advance(inst, graph, next_ids, definition))
                    return notify_ids

                created_task_ids: list[int] = []
                if apv_rel == 'sequential':
                    t = TaskInstance(
                        instance_id=inst.id,
                        node_id=nid,
                        node_type=ntype,
                        assignee_id=pending_assignees[0],
                        status='pending',
                        action_meta=json.dumps(
                            {
                                'sequential_queue': pending_assignees,
                                'sequential_index': 0,
                            },
                            ensure_ascii=False,
                        ),
                    )
                    db.session.add(t)
                    db.session.flush()
                    created_task_ids.append(t.id)
                else:
                    for uid in pending_assignees:
                        t = TaskInstance(
                            instance_id=inst.id,
                            node_id=nid,
                            node_type=ntype,
                            assignee_id=uid,
                            status='pending',
                        )
                        db.session.add(t)
                        db.session.flush()
                        created_task_ids.append(t.id)
                if created_task_ids:
                    notify_ids.extend(created_task_ids)
                self._try_sequential_continue(inst, graph, definition)
                return notify_ids

        db.session.flush()
        return notify_ids

    def _spawn_next_sequential_task(self, inst: WorkflowInstance, completed: TaskInstance) -> int | None:
        if not completed.action_meta:
            return None
        try:
            meta = json.loads(completed.action_meta)
        except (json.JSONDecodeError, TypeError):
            return None
        queue = meta.get('sequential_queue')
        idx = meta.get('sequential_index', 0)
        if not queue or idx + 1 >= len(queue):
            return None
        next_idx = idx + 1
        exists = inst.tasks.filter_by(
            node_id=completed.node_id,
            assignee_id=queue[next_idx],
            status='pending',
        ).count()
        if exists:
            return None
        t = TaskInstance(
            instance_id=inst.id,
            node_id=completed.node_id,
            node_type=completed.node_type,
            assignee_id=queue[next_idx],
            status='pending',
            action_meta=json.dumps(
                {'sequential_queue': queue, 'sequential_index': next_idx},
                ensure_ascii=False,
            ),
        )
        db.session.add(t)
        db.session.flush()
        return t.id

    def _try_sequential_continue(
        self,
        inst: WorkflowInstance,
        graph: dict,
        definition: WorkflowDefinition,
    ) -> None:
        for task in inst.tasks.filter_by(status='pending').all():
            if not task.action_meta:
                continue
            try:
                meta = json.loads(task.action_meta)
            except (json.JSONDecodeError, TypeError):
                continue
            queue = meta.get('sequential_queue')
            idx = meta.get('sequential_index', 0)
            if not queue or idx is None:
                continue
            approved_count = inst.tasks.filter_by(
                node_id=task.node_id,
                status='approved',
            ).count()
            if approved_count <= idx:
                continue
            next_idx = idx + 1
            if next_idx < len(queue):
                db.session.add(
                    TaskInstance(
                        instance_id=inst.id,
                        node_id=task.node_id,
                        node_type=task.node_type,
                        assignee_id=queue[next_idx],
                        status='pending',
                        action_meta=json.dumps(
                            {'sequential_queue': queue, 'sequential_index': next_idx},
                            ensure_ascii=False,
                        ),
                    ),
                )

    def save_draft(
        self,
        definition: WorkflowDefinition,
        initiator_id: int,
        company_id: int,
        department_id: int | None = None,
        org_unit_id: int | None = None,
        variables: dict | None = None,
        instance: WorkflowInstance | None = None,
    ) -> WorkflowInstance:
        """保存或更新流程草稿（不校验表单、不发起审批）。"""
        user = User.query.get(initiator_id)
        if not user or not user_can_apply_workflow(user, definition, company_id):
            raise ValueError('无权在该公司下发起该流程，或您不在该流程的发起可见范围内')

        vars_payload = dict(variables or {})
        vars_payload.setdefault('org', {})
        vars_payload['org'].update({
            'company_id': company_id,
            'department_id': department_id,
            'org_unit_id': org_unit_id,
            'initiator_id': initiator_id,
        })

        now = datetime.now()
        if instance:
            if instance.status != 'draft':
                raise ValueError('仅草稿可更新')
            if instance.initiator_id != initiator_id:
                raise ValueError('无权修改该草稿')
            instance.company_id = company_id
            instance.department_id = department_id
            instance.org_unit_id = org_unit_id
            instance.variables = json.dumps(vars_payload, ensure_ascii=False)
            instance.updated_at = now
            db.session.commit()
            return instance

        inst = WorkflowInstance(
            definition_id=definition.id,
            initiator_id=initiator_id,
            company_id=company_id,
            department_id=department_id,
            org_unit_id=org_unit_id,
            business_sector_id=definition.business_sector_id,
            status='draft',
            variables=json.dumps(vars_payload, ensure_ascii=False),
            current_node_ids=json.dumps([]),
            started_at=now,
            updated_at=now,
        )
        db.session.add(inst)
        db.session.flush()
        ensure_instance_public_uuid(inst)
        db.session.commit()
        return inst

    def submit_draft(self, instance: WorkflowInstance, initiator_id: int) -> WorkflowInstance:
        """将草稿正式提交并进入审批流程。"""
        if instance.status != 'draft':
            raise ValueError('该申请已不是草稿')
        if instance.initiator_id != initiator_id:
            raise ValueError('无权提交该草稿')

        definition = instance.definition
        if not definition:
            raise ValueError('流程模板不存在')

        graph = parse_graph(definition.process_graph)
        start_node = find_node(graph, 'start')
        if not start_node:
            raise ValueError('流程图缺少开始节点')

        vars_payload = parse_variables(instance.variables)
        now = datetime.now()
        instance.status = 'running'
        if not instance.display_no:
            instance.display_no = allocate_workflow_display_no()
        instance.started_at = now
        instance.updated_at = now
        ensure_instance_public_uuid(instance)

        self._append_timeline(instance.id, initiator_id, 'submit', start_node.get('id'), '已提交')
        next_ids = resolve_next_node_ids(graph, start_node.get('id'), vars_payload)
        if not next_ids:
            next_ids = _next_from_start_legacy(graph, start_node)
        notify_ids = self._advance(instance, graph, next_ids, definition)
        db.session.commit()
        app = current_app._get_current_object()
        notify_instance_result_if_finished(app, instance)
        if notify_ids:
            notify_pending_tasks(app, notify_ids)
        return instance

    def withdraw(self, instance: WorkflowInstance, actor_id: int) -> WorkflowInstance:
        """发起人撤回：审批中可随时撤回；已通过时须流程设置允许。"""
        if instance.initiator_id != actor_id:
            raise ValueError('仅发起人可撤回申请')
        settings = merge_settings(
            instance.definition.settings if instance.definition else None,
        )
        if instance.status == 'running':
            pass
        elif instance.status == 'approved':
            if not settings.get('allow_revoke_after_approved'):
                raise ValueError('该流程未开启「通过后允许撤回」')
        else:
            raise ValueError('当前状态不可撤回')

        now = datetime.now()
        for task in instance.tasks.filter_by(status='pending').all():
            task.status = 'cancelled'
            task.completed_at = now

        was_approved = instance.status == 'approved'
        instance.status = 'cancelled'
        instance.finished_at = now
        instance.current_node_ids = json.dumps([])
        if was_approved:
            from app.services.receipt_duplicate_service import clear_receipt_usage_for_instance

            clear_receipt_usage_for_instance(instance.id)
        self._append_timeline(instance.id, actor_id, 'cancel', None, '申请人撤回')
        db.session.commit()
        return instance

    def _append_timeline(
        self,
        instance_id: int,
        actor_id: int | None,
        action: str,
        node_id: str | None,
        comment: str,
        payload: dict | None = None,
    ) -> None:
        db.session.add(
            InstanceTimeline(
                instance_id=instance_id,
                actor_id=actor_id,
                action=action,
                node_id=node_id,
                comment=comment,
                payload=json.dumps(payload, ensure_ascii=False) if payload else None,
            ),
        )


def get_parallel_branch_targets(graph: dict, node_id: str) -> list:
    targets = []
    for edge in graph.get('edges') or []:
        if edge.get('source') == node_id and edge.get('target'):
            targets.append(edge['target'])
    return targets


def _next_from_start_legacy(graph: dict, start_node: dict) -> list:
    sid = start_node.get('id')
    out = []
    for edge in graph.get('edges') or []:
        if edge.get('source') == sid:
            out.append(edge.get('target'))
    if not out:
        nxt = start_node.get('next')
        if isinstance(nxt, list):
            return nxt
    return [x for x in out if x]
