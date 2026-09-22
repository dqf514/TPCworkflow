# -*- coding: utf-8 -*-
from datetime import datetime

from app.extensions import db

system_role_permissions = db.Table(
    'system_role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('system_roles.id'), primary_key=True),
    db.Column(
        'permission_id',
        db.Integer,
        db.ForeignKey('system_permissions.id'),
        primary_key=True,
    ),
)


class SystemRole(db.Model):
    """系统功能角色（管理员、流程设计师等）。"""
    __tablename__ = 'system_roles'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())

    permissions = db.relationship(
        'SystemPermission',
        secondary=system_role_permissions,
        lazy='joined',
    )


class SystemPermission(db.Model):
    __tablename__ = 'system_permissions'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)


class UserSystemRole(db.Model):
    __tablename__ = 'user_system_roles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role_id = db.Column(
        db.Integer,
        db.ForeignKey('system_roles.id'),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', name='uq_user_system_role'),
    )


class FlowRole(db.Model):
    """流程审批角色（财务、法务等），与系统角色分离。"""
    __tablename__ = 'flow_roles'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(512))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())


class FlowRoleMember(db.Model):
    """流程角色成员，可按公司/部门限定范围。"""
    __tablename__ = 'flow_role_members'

    id = db.Column(db.Integer, primary_key=True)
    flow_role_id = db.Column(
        db.Integer,
        db.ForeignKey('flow_roles.id'),
        nullable=False,
        index=True,
    )
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())

    flow_role = db.relationship('FlowRole')

    __table_args__ = (
        db.UniqueConstraint(
            'flow_role_id',
            'user_id',
            'company_id',
            'department_id',
            name='uq_flow_role_member',
        ),
    )
