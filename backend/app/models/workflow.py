# -*- coding: utf-8 -*-
from datetime import datetime

from app.extensions import db


class WorkflowDefinition(db.Model):
    """流程模板定义。"""
    __tablename__ = 'workflow_definitions'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(32), default='draft', nullable=False)
    scope_type = db.Column(db.String(32), default='global', nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), index=True)
    company_ids = db.Column(db.Text)
    form_definition_id = db.Column(
        db.Integer,
        db.ForeignKey('form_definitions.id'),
        index=True,
    )
    business_sector_id = db.Column(db.Integer, db.ForeignKey('business_sectors.id'), index=True)
    form_schema = db.Column(db.Text)
    process_graph = db.Column(db.Text)
    settings = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    __table_args__ = (
        db.UniqueConstraint('key', 'version', name='uq_workflow_def_key_version'),
    )


class WorkflowInstance(db.Model):
    """流程运行实例（带公司上下文）。"""
    __tablename__ = 'workflow_instances'

    id = db.Column(db.Integer, primary_key=True)
    public_uuid = db.Column(db.String(36), unique=True, index=True)
    display_no = db.Column(db.String(32), unique=True, index=True)
    definition_id = db.Column(
        db.Integer,
        db.ForeignKey('workflow_definitions.id'),
        nullable=False,
        index=True,
    )
    business_type = db.Column(db.String(64), index=True)
    business_id = db.Column(db.String(64), index=True)
    initiator_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True,
    )
    company_id = db.Column(
        db.Integer,
        db.ForeignKey('companies.id'),
        nullable=False,
        index=True,
    )
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    business_sector_id = db.Column(db.Integer, db.ForeignKey('business_sectors.id'), index=True)
    status = db.Column(db.String(32), default='running', nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
    current_node_ids = db.Column(db.Text)
    variables = db.Column(db.Text)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now())
    finished_at = db.Column(db.DateTime)

    definition = db.relationship('WorkflowDefinition')
    tasks = db.relationship(
        'TaskInstance',
        back_populates='instance',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )


class TaskInstance(db.Model):
    """待办任务。"""
    __tablename__ = 'task_instances'

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(
        db.Integer,
        db.ForeignKey('workflow_instances.id'),
        nullable=False,
        index=True,
    )
    node_id = db.Column(db.String(64), nullable=False)
    node_type = db.Column(db.String(32), nullable=False)
    assignee_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(32), default='pending', nullable=False, index=True)
    action_meta = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    completed_at = db.Column(db.DateTime)

    instance = db.relationship('WorkflowInstance', back_populates='tasks')


class TaskEmailToken(db.Model):
    """邮件内快速审批链接令牌（一次性）。"""
    __tablename__ = 'task_email_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey('task_instances.id'),
        nullable=False,
        index=True,
    )
    assignee_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True,
    )
    action = db.Column(db.String(16), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())


class InstanceTimeline(db.Model):
    """审批审计流水（只追加）。"""
    __tablename__ = 'instance_timelines'

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(
        db.Integer,
        db.ForeignKey('workflow_instances.id'),
        nullable=False,
        index=True,
    )
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(64), nullable=False)
    node_id = db.Column(db.String(64))
    comment = db.Column(db.Text)
    payload = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(), index=True)


class InstanceViewState(db.Model):
    """用户查看流程实例进度的时间水位（用于发起人未读进度角标）。"""
    __tablename__ = 'instance_view_states'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        primary_key=True,
    )
    instance_id = db.Column(
        db.Integer,
        db.ForeignKey('workflow_instances.id'),
        primary_key=True,
    )
    last_seen_at = db.Column(db.DateTime, nullable=False)
