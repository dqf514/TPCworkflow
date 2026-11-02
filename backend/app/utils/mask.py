# -*- coding: utf-8 -*-
"""敏感信息脱敏工具。

通知邮件正文里可能带有可直接复用的一次性凭证（登录验证码、邮件快捷审批 token）。
这些正文会写入 notification_logs 并对管理员可见，必须在落库与读出两侧都脱敏，
避免「通知日志接口」退化成「凭证泄露接口」。
"""
import re

# URL 查询参数中的凭证：?token=xxx / &code=xxx ...
_SENSITIVE_PARAM_RE = re.compile(
    r'([?&](?:token|code|otp|verify_code|sign|secret|password)=)([^&\s\'"<>]+)',
    re.I,
)

# Authorization: Bearer xxxxx
_BEARER_RE = re.compile(r'(Bearer\s+)([A-Za-z0-9_\-\.=]{12,})', re.I)

# 正文里以自然语言出现的验证码：「您的登录验证码为：931127」
_OTP_RE = re.compile(r'(验证码\s*(?:为|是)?\s*[:：]?\s*)(\d{4,8})')

MASK = '******'


def mask_sensitive_text(text) -> str:
    """遮蔽文本中的 URL 凭证参数、Bearer Token 与明文验证码。"""
    if not text:
        return text
    if not isinstance(text, str):
        text = str(text)
    text = _SENSITIVE_PARAM_RE.sub(r'\1' + MASK, text)
    text = _BEARER_RE.sub(r'\1' + MASK, text)
    text = _OTP_RE.sub(r'\1' + MASK, text)
    return text


def mask_code(text, code) -> str:
    """把正文中出现的验证码替换为掩码（验证码长度 < 4 时不处理，避免误伤）。"""
    if not text or not code or len(str(code)) < 4:
        return text
    return text.replace(str(code), MASK)
