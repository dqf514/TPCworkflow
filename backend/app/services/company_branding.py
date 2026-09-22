# -*- coding: utf-8 -*-
"""系统唯一组织（公司）名称、Logo 与主公司实体同步。"""
from __future__ import annotations

import os

from app.extensions import db
from app.models import Company, SystemSetting
from app.utils.branding import APP_DISPLAY_NAME

PRIMARY_COMPANY_CODE = 'SYSTEM'
SETTING_COMPANY_NAME = 'COMPANY_NAME'
SETTING_COMPANY_LOGO = 'COMPANY_LOGO'
DEFAULT_COMPANY_NAME = APP_DISPLAY_NAME
BRANDING_UPLOAD_SUBDIR = 'uploads/branding'


def get_company_name() -> str:
    row = SystemSetting.query.get(SETTING_COMPANY_NAME)
    if row and (row.value or '').strip():
        return row.value.strip()
    company = Company.query.filter_by(code=PRIMARY_COMPANY_CODE, is_active=True).first()
    if company and company.name:
        return company.name
    legacy = Company.query.filter_by(is_active=True).order_by(Company.sort_order, Company.id).first()
    if legacy and legacy.name:
        return legacy.name
    return DEFAULT_COMPANY_NAME


def get_company_logo_path() -> str | None:
    row = SystemSetting.query.get(SETTING_COMPANY_LOGO)
    if not row or not (row.value or '').strip():
        return None
    rel = row.value.strip().replace('\\', '/')
    if not rel.startswith(BRANDING_UPLOAD_SUBDIR + '/'):
        return None
    return rel


def get_company_logo_url() -> str | None:
    rel = get_company_logo_path()
    if not rel:
        return None
    return f'/api/v1/public/files/{rel}'


def set_company_logo_path(rel_path: str) -> None:
    rel_path = rel_path.replace('\\', '/')
    row = SystemSetting.query.get(SETTING_COMPANY_LOGO)
    if not row:
        row = SystemSetting(key=SETTING_COMPANY_LOGO)
        db.session.add(row)
    row.value = rel_path
    db.session.flush()


def clear_company_logo() -> str | None:
    """删除磁盘上的 Logo 并清空设置，返回已删除的相对路径。"""
    rel = get_company_logo_path()
    row = SystemSetting.query.get(SETTING_COMPANY_LOGO)
    if row:
        row.value = ''
    db.session.flush()
    return rel


def resolve_logo_abs_path(rel: str, app_root: str) -> str:
    base = os.path.abspath(os.path.join(app_root, '..'))
    return os.path.join(base, rel.replace('..', '').replace('\\', '/'))


def get_primary_company() -> Company:
    company = Company.query.filter_by(code=PRIMARY_COMPANY_CODE).first()
    if company:
        return company
    legacy = Company.query.filter_by(is_active=True).order_by(Company.sort_order, Company.id).first()
    if legacy:
        legacy.code = PRIMARY_COMPANY_CODE
        if not SystemSetting.query.get(SETTING_COMPANY_NAME):
            row = SystemSetting(key=SETTING_COMPANY_NAME, value=legacy.name)
            db.session.add(row)
        db.session.flush()
        return legacy
    name = get_company_name()
    company = Company(name=name, code=PRIMARY_COMPANY_CODE, sort_order=0, is_active=True)
    db.session.add(company)
    db.session.flush()
    return company


def sync_company_name(name: str) -> Company:
    name = (name or '').strip() or DEFAULT_COMPANY_NAME
    company = get_primary_company()
    company.name = name
    company.is_active = True
    row = SystemSetting.query.get(SETTING_COMPANY_NAME)
    if not row:
        row = SystemSetting(key=SETTING_COMPANY_NAME)
        db.session.add(row)
    row.value = name
    db.session.flush()
    return company
