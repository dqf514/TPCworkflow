# -*- coding: utf-8 -*-
"""开发环境：创建新表并补充词典种子。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.models import Department, UserOrgMembership
from scripts.bootstrap import ensure_bootstrap
from scripts.seed_i18n import seed_all_locales


def _ensure_columns() -> None:
    """SQLite 已有库补充新列（create_all 不会改表结构）。"""
    insp = inspect(db.engine)
    table_names = set(insp.get_table_names())
    if 'admin_email_confirm_codes' not in table_names:
        db.create_all()
        table_names = set(inspect(db.engine).get_table_names())
    if 'companies' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('companies')}
        if 'holiday_region' not in cols:
            db.session.execute(
                text("ALTER TABLE companies ADD COLUMN holiday_region VARCHAR(16) DEFAULT 'CN' NOT NULL"),
            )
    if 'workflow_definitions' in table_names:
        cols = {c['name'] for c in insp.get_columns('workflow_definitions')}
        if 'form_definition_id' not in cols:
            db.session.execute(
                text('ALTER TABLE workflow_definitions ADD COLUMN form_definition_id INTEGER'),
            )
        if 'business_sector_id' not in cols:
            db.session.execute(
                text('ALTER TABLE workflow_definitions ADD COLUMN business_sector_id INTEGER'),
            )
    if 'form_definitions' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('form_definitions')}
        if 'business_sector_id' not in cols:
            db.session.execute(
                text('ALTER TABLE form_definitions ADD COLUMN business_sector_id INTEGER'),
            )
        if 'icon' not in cols:
            db.session.execute(text('ALTER TABLE form_definitions ADD COLUMN icon VARCHAR(64)'))
        if 'published_at' not in cols:
            db.session.execute(text('ALTER TABLE form_definitions ADD COLUMN published_at DATETIME'))
            db.session.execute(
                text(
                    "UPDATE form_definitions SET published_at = updated_at "
                    "WHERE status = 'published' AND published_at IS NULL",
                ),
            )
    if 'workflow_instances' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('workflow_instances')}
        if 'business_sector_id' not in cols:
            db.session.execute(
                text('ALTER TABLE workflow_instances ADD COLUMN business_sector_id INTEGER'),
            )
        if 'updated_at' not in cols:
            db.session.execute(
                text('ALTER TABLE workflow_instances ADD COLUMN updated_at DATETIME'),
            )
        if 'org_unit_id' not in cols:
            db.session.execute(
                text('ALTER TABLE workflow_instances ADD COLUMN org_unit_id INTEGER'),
            )
    if 'user_org_memberships' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('user_org_memberships')}
        if 'role_in_dept' not in cols:
            db.session.execute(
                text("ALTER TABLE user_org_memberships ADD COLUMN role_in_dept VARCHAR(32) DEFAULT 'member'"),
            )
    if 'users' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('users')}
        if 'job_title' not in cols:
            db.session.execute(text('ALTER TABLE users ADD COLUMN job_title VARCHAR(128)'))
        if 'holiday_regions' not in cols:
            db.session.execute(
                text("ALTER TABLE users ADD COLUMN holiday_regions VARCHAR(128) DEFAULT '' NOT NULL"),
            )
    if 'option_sets' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('option_sets')}
        if 'set_type' not in cols:
            db.session.execute(
                text("ALTER TABLE option_sets ADD COLUMN set_type VARCHAR(16) DEFAULT 'option'"),
            )
        if 'data_scope' not in cols:
            db.session.execute(
                text("ALTER TABLE option_sets ADD COLUMN data_scope VARCHAR(16) DEFAULT 'mixed'"),
            )
            db.session.commit()
            db.session.execute(
                text("UPDATE option_sets SET data_scope = 'personal' WHERE code = 'personal_account'"),
            )
            db.session.execute(
                text("UPDATE option_sets SET data_scope = 'company' WHERE code = 'payee_list'"),
            )
    if 'workflow_instances' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('workflow_instances')}
        if 'public_uuid' not in cols:
            db.session.execute(text('ALTER TABLE workflow_instances ADD COLUMN public_uuid VARCHAR(36)'))
            db.session.commit()
            from app.models import WorkflowInstance
            import uuid as _uuid

            rows = WorkflowInstance.query.filter(
                (WorkflowInstance.public_uuid.is_(None)) | (WorkflowInstance.public_uuid == ''),
            ).all()
            for row in rows:
                row.public_uuid = str(_uuid.uuid4())
            db.session.commit()
            try:
                db.session.execute(
                    text('CREATE UNIQUE INDEX IF NOT EXISTS ix_workflow_instances_public_uuid ON workflow_instances (public_uuid)'),
                )
            except Exception:
                pass
    if 'workflow_instances' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('workflow_instances')}
        if 'display_no' not in cols:
            db.session.execute(
                text('ALTER TABLE workflow_instances ADD COLUMN display_no VARCHAR(32)'),
            )
    if 'option_set_records' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('option_set_records')}
        if 'owner_user_id' not in cols:
            db.session.execute(
                text('ALTER TABLE option_set_records ADD COLUMN owner_user_id INTEGER'),
            )
        if 'created_at' not in cols:
            db.session.execute(text('ALTER TABLE option_set_records ADD COLUMN created_at DATETIME'))
        if 'updated_at' not in cols:
            db.session.execute(text('ALTER TABLE option_set_records ADD COLUMN updated_at DATETIME'))
    if 'option_set_columns' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('option_set_columns')}
        if 'span' not in cols:
            db.session.execute(
                text('ALTER TABLE option_set_columns ADD COLUMN span INTEGER DEFAULT 24 NOT NULL'),
            )
    if 'task_email_tokens' not in insp.get_table_names():
        from app.models import TaskEmailToken

        TaskEmailToken.__table__.create(db.engine)
    if 'instance_view_states' not in insp.get_table_names():
        from app.models import InstanceViewState

        InstanceViewState.__table__.create(db.engine)
    if 'notification_logs' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('notification_logs')}
        if 'mail_type' not in cols:
            db.session.execute(text('ALTER TABLE notification_logs ADD COLUMN mail_type VARCHAR(32)'))
        if 'recipient' not in cols:
            db.session.execute(text('ALTER TABLE notification_logs ADD COLUMN recipient VARCHAR(256)'))
        if 'task_id' not in cols:
            db.session.execute(text('ALTER TABLE notification_logs ADD COLUMN task_id INTEGER'))
        if 'instance_id' not in cols:
            db.session.execute(text('ALTER TABLE notification_logs ADD COLUMN instance_id INTEGER'))
    if 'login_access_logs' not in insp.get_table_names():
        from app.models import LoginAccessLog

        LoginAccessLog.__table__.create(db.engine)
    if 'finance_export_mappings' not in insp.get_table_names():
        from app.models import FinanceExportMapping

        FinanceExportMapping.__table__.create(db.engine)
    if 'print_templates' not in insp.get_table_names():
        from app.models import PrintTemplate

        PrintTemplate.__table__.create(db.engine)
    db.session.commit()


def _migrate_user_job_title_to_memberships() -> int:
    """历史全公司职位写入主部门任职职务，并清空 users.job_title。"""
    moved = 0
    rows = db.session.execute(
        text("SELECT id, job_title FROM users WHERE job_title IS NOT NULL AND TRIM(job_title) != ''"),
    ).fetchall()
    for user_id, title in rows:
        title = (title or '').strip()
        if not title:
            continue
        m = (
            UserOrgMembership.query.filter_by(user_id=user_id)
            .order_by(UserOrgMembership.is_primary.desc(), UserOrgMembership.id)
            .first()
        )
        if m and not (m.job_title or '').strip():
            m.job_title = title
            moved += 1
        db.session.execute(text('UPDATE users SET job_title = NULL WHERE id = :id'), {'id': user_id})
    db.session.commit()
    return moved


def _purge_orphan_inactive_departments() -> int:
    """清理无任职、无子部门的停用部门（历史软删除残留）。"""
    removed = 0
    while True:
        stale = (
            Department.query.filter_by(is_active=False)
            .order_by(Department.id.desc())
            .all()
        )
        deleted_any = False
        for d in stale:
            if Department.query.filter_by(parent_id=d.id).first():
                continue
            if UserOrgMembership.query.filter_by(department_id=d.id).first():
                continue
            db.session.delete(d)
            removed += 1
            deleted_any = True
        if not deleted_any:
            break
        db.session.commit()
    return removed


def _rebuild_departments_sqlite() -> None:
    """SQLite 无法 ALTER 删除表内 UNIQUE，需重建 departments 表。"""
    db.session.execute(text('PRAGMA foreign_keys=OFF'))
    db.session.execute(
        text(
            """
            CREATE TABLE departments_new (
                id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                parent_id INTEGER,
                name VARCHAR(128) NOT NULL,
                sort_order INTEGER,
                is_active BOOLEAN NOT NULL,
                created_at DATETIME,
                PRIMARY KEY (id),
                FOREIGN KEY(company_id) REFERENCES companies (id),
                FOREIGN KEY(parent_id) REFERENCES departments (id)
            )
            """,
        ),
    )
    db.session.execute(
        text(
            """
            INSERT INTO departments_new
                (id, company_id, parent_id, name, sort_order, is_active, created_at)
            SELECT id, company_id, parent_id, name, sort_order, is_active, created_at
            FROM departments
            """,
        ),
    )
    db.session.execute(text('DROP TABLE departments'))
    db.session.execute(text('ALTER TABLE departments_new RENAME TO departments'))
    db.session.execute(
        text(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_department_company_parent_name '
            'ON departments (company_id, parent_id, name)',
        ),
    )
    db.session.execute(
        text('CREATE INDEX IF NOT EXISTS ix_departments_company_id ON departments (company_id)'),
    )
    db.session.execute(
        text('CREATE INDEX IF NOT EXISTS ix_departments_parent_id ON departments (parent_id)'),
    )
    db.session.execute(text('PRAGMA foreign_keys=ON'))
    db.session.commit()


def _sqlite_departments_has_legacy_unique() -> bool:
    ddl = db.session.execute(
        text("SELECT sql FROM sqlite_master WHERE type='table' AND name='departments'"),
    ).scalar()
    if not ddl:
        return False
    return 'uq_department_company_name' in ddl or 'UNIQUE (company_id, name)' in ddl.replace(' ', '')


def _drop_legacy_department_name_unique() -> list[str]:
    """移除「公司+名称」旧唯一约束/索引，保留「公司+上级+名称」。"""
    insp = inspect(db.engine)
    if 'departments' not in insp.get_table_names():
        return []
    dialect = db.engine.dialect.name
    dropped: list[str] = []
    legacy_cols = ('company_id', 'name')

    for idx in insp.get_indexes('departments'):
        if not idx.get('unique'):
            continue
        cols = tuple(idx.get('column_names') or ())
        if cols != legacy_cols:
            continue
        name = idx['name']
        if dialect == 'sqlite':
            db.session.execute(text(f'DROP INDEX IF EXISTS {name}'))
        elif dialect in ('mysql', 'mariadb'):
            db.session.execute(text(f'ALTER TABLE departments DROP INDEX `{name}`'))
        dropped.append(name)

    if dialect in ('mysql', 'mariadb'):
        for uc in insp.get_unique_constraints('departments'):
            cols = tuple(uc.get('column_names') or ())
            if cols != legacy_cols:
                continue
            name = uc['name']
            db.session.execute(text(f'ALTER TABLE departments DROP INDEX `{name}`'))
            dropped.append(name)

    return dropped


def _migrate_department_unique_constraint() -> None:
    """部门名称唯一约束：公司+上级+名称（允许不同上级下同名）。"""
    insp = inspect(db.engine)
    if 'departments' not in insp.get_table_names():
        return
    dialect = db.engine.dialect.name
    if dialect == 'sqlite' and _sqlite_departments_has_legacy_unique():
        _rebuild_departments_sqlite()
        print('已重建 departments 表：允许不同上级下部门同名')
        return
    dropped = _drop_legacy_department_name_unique()
    indexes = {idx['name'] for idx in insp.get_indexes('departments')}
    if dialect == 'sqlite':
        if 'uq_department_company_parent_name' not in indexes:
            db.session.execute(
                text(
                    'CREATE UNIQUE INDEX IF NOT EXISTS uq_department_company_parent_name '
                    'ON departments (company_id, parent_id, name)',
                ),
            )
    elif dialect in ('mysql', 'mariadb'):
        if 'uq_department_company_parent_name' not in indexes:
            db.session.execute(
                text(
                    'ALTER TABLE departments ADD CONSTRAINT uq_department_company_parent_name '
                    'UNIQUE (company_id, parent_id, name)',
                ),
            )
    db.session.commit()
    if dropped:
        print(f'已移除旧部门唯一约束: {", ".join(dropped)}')


def upgrade_all() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        _ensure_columns()
        _migrate_department_unique_constraint()
        job_moved = _migrate_user_job_title_to_memberships()
        purged = _purge_orphan_inactive_departments()
        added = seed_all_locales()
        ensure_bootstrap()
        receipt_backfill = 0
        if 'receipt_usage_records' in inspect(db.engine).get_table_names():
            from app.services.receipt_duplicate_service import backfill_receipt_usage_from_approved

            receipt_backfill = backfill_receipt_usage_from_approved()
        print_tpl_added = 0
        if 'print_templates' in inspect(db.engine).get_table_names():
            from app.services.print_template_service import ensure_builtin_templates

            print_tpl_added = ensure_builtin_templates()
        print(
            f'数据库已升级，词典补缺/空值 {added} 条（不覆盖已有译文；'
            f'强制同步种子请设 I18N_FORCE_SEED_SYNC=1），'
            f'迁移全公司职位 {job_moved} 条，清理停用部门 {purged} 个，'
            f'票据防重复登记 {receipt_backfill} 条已通过申请，'
            f'内置打印模板 {print_tpl_added} 个',
        )


if __name__ == '__main__':
    upgrade_all()
