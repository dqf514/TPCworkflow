# -*- coding: utf-8 -*-
from app.extensions import db
from app.models import User


def normalize_email(email: str | None) -> str:
    return (email or '').strip().lower()


def normalize_phone(phone: str | None) -> str:
    return ''.join(ch for ch in (phone or '').strip() if ch.isdigit())


def find_user_by_login_identifier(identifier: str) -> User | None:
    ident = (identifier or '').strip()
    if not ident:
        return None
    if '@' in ident:
        return User.query.filter(
            db.func.lower(User.email) == normalize_email(ident),
            User.is_active.is_(True),
        ).first()
    phone = normalize_phone(ident)
    if phone:
        user = User.query.filter_by(phone=phone, is_active=True).first()
        if user:
            return user
    return User.query.filter(
        db.func.lower(User.username) == ident.lower(),
        User.is_active.is_(True),
    ).first()
