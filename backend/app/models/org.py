# -*- coding: utf-8 -*-
from datetime import datetime

from app.extensions import db


class Company(db.Model):
    """公司实体（多组织，非多租户）。"""
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=True, index=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    holiday_region = db.Column(db.String(16), default='CN', nullable=False)

    departments = db.relationship(
        'Department',
        back_populates='company',
        lazy='dynamic',
        order_by='Department.sort_order',
        cascade='all, delete-orphan',
    )


class Department(db.Model):
    """部门（隶属公司，可树形扩展 parent_id）。"""
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey('companies.id'),
        nullable=False,
        index=True,
    )
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())

    company = db.relationship('Company', back_populates='departments')
    parent = db.relationship('Department', remote_side=[id], backref='children')

    __table_args__ = (
        db.UniqueConstraint(
            'company_id',
            'parent_id',
            'name',
            name='uq_department_company_parent_name',
        ),
    )


class UserOrgMembership(db.Model):
    """用户在公司+部门下的任职（可多任职、设主部门）。"""
    __tablename__ = 'user_org_memberships'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
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
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id'),
        nullable=False,
        index=True,
    )
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    role_in_dept = db.Column(db.String(32), default='member', nullable=False)
    job_title = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())

    user = db.relationship('User', back_populates='org_memberships')
    company = db.relationship('Company')
    department = db.relationship('Department')

    __table_args__ = (
        db.UniqueConstraint(
            'user_id',
            'company_id',
            'department_id',
            name='uq_user_org_membership',
        ),
    )
