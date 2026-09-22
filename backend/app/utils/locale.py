# -*- coding: utf-8 -*-
from flask import request
from flask_login import current_user

from config import Config


def resolve_request_locale() -> str:
    if current_user.is_authenticated and getattr(current_user, 'locale', None):
        return current_user.locale
    header = request.headers.get('Accept-Language', '')
    if header:
        part = header.split(',')[0].strip()
        if part:
            return part.replace('_', '-')
    q = request.args.get('locale')
    if q:
        return q.replace('_', '-')
    return Config.DEFAULT_LOCALE
