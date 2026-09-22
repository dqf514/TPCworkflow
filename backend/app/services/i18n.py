# -*- coding: utf-8 -*-
from datetime import datetime

from app.extensions import db
from app.models import I18nBundleMeta, I18nLocale, I18nMessage
from config import Config


def get_default_locale() -> str:
    row = I18nLocale.query.filter_by(is_default=True, is_enabled=True).first()
    return row.code if row else Config.DEFAULT_LOCALE


def t(key: str, locale: str | None = None, **kwargs) -> str:
    """翻译：key 格式 namespace.msg_key 或完整键。"""
    locale = locale or get_default_locale()
    if '.' not in key:
        return key
    namespace, msg_key = key.split('.', 1)
    text = _lookup(namespace, msg_key, locale)
    if text is None and locale != get_default_locale():
        text = _lookup(namespace, msg_key, get_default_locale())
    if text is None:
        return key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def _lookup(namespace: str, msg_key: str, locale: str) -> str | None:
    row = I18nMessage.query.filter_by(
        namespace=namespace,
        msg_key=msg_key,
        locale=locale,
    ).first()
    return row.msg_value if row else None


def flatten_messages(rows: list[I18nMessage]) -> dict[str, str]:
    out = {}
    for row in rows:
        out[f'{row.namespace}.{row.msg_key}'] = row.msg_value
    return out


def get_bundle_version(locale: str) -> int:
    meta = I18nBundleMeta.query.get(locale)
    return int(meta.version) if meta else 1


def bump_bundle_version(locale: str | None = None) -> None:
    locales = [locale] if locale else [r.code for r in I18nLocale.query.filter_by(is_enabled=True)]
    for code in locales:
        meta = I18nBundleMeta.query.get(code)
        if not meta:
            meta = I18nBundleMeta(locale=code, version=1)
            db.session.add(meta)
        else:
            meta.version = (meta.version or 0) + 1
        meta.published_at = datetime.now()
    db.session.commit()


def load_messages(locale: str, namespaces: list[str] | None = None) -> dict[str, str]:
    q = I18nMessage.query.filter_by(locale=locale)
    if namespaces:
        q = q.filter(I18nMessage.namespace.in_(namespaces))
    return flatten_messages(q.all())
