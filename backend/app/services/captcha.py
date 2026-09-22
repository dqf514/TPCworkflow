# -*- coding: utf-8 -*-
"""登录图形验证码：中等干扰，兼顾防爬与可读性。"""
from __future__ import annotations

import base64
import io
import math
import os
import random
import secrets
from datetime import datetime, timedelta

from flask import session
from PIL import Image, ImageDraw, ImageFont
from werkzeug.security import check_password_hash, generate_password_hash

# 排除易混淆字符 0/O、1/I/L
_CAPTCHA_CHARS = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'
_CAPTCHA_LEN = 4
_CAPTCHA_TTL_MINUTES = 5
_SESSION_KEY = 'login_captcha'

_FONT_CANDIDATES = [
    'C:/Windows/Fonts/arialbd.ttf',
    'C:/Windows/Fonts/arial.ttf',
    'C:/Windows/Fonts/msyh.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _random_text() -> str:
    return ''.join(secrets.choice(_CAPTCHA_CHARS) for _ in range(_CAPTCHA_LEN))


def _build_image(text: str) -> bytes:
    width, height = 148, 52
    img = Image.new('RGB', (width, height), (245, 246, 250))
    draw = ImageDraw.Draw(img)

    # 浅色渐变底
    for y in range(height):
        r = int(235 + (y / height) * 15)
        g = int(238 + (y / height) * 10)
        b = int(248 - (y / height) * 8)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 干扰曲线
    for _ in range(2):
        pts = []
        amp = random.uniform(4, 8)
        freq = random.uniform(0.04, 0.09)
        phase = random.uniform(0, math.pi * 2)
        y0 = random.randint(12, height - 12)
        color = (
            random.randint(120, 180),
            random.randint(130, 190),
            random.randint(160, 210),
        )
        for x in range(width):
            y = int(y0 + math.sin(x * freq + phase) * amp)
            pts.append((x, y))
        draw.line(pts, fill=color, width=1)

    # 干扰线
    for _ in range(3):
        draw.line(
            [
                (random.randint(0, width // 3), random.randint(0, height)),
                (random.randint(width // 2, width), random.randint(0, height)),
            ],
            fill=(
                random.randint(150, 200),
                random.randint(150, 200),
                random.randint(170, 220),
            ),
            width=1,
        )

    # 噪点
    for _ in range(55):
        draw.point(
            (random.randint(0, width - 1), random.randint(0, height - 1)),
            fill=(
                random.randint(100, 200),
                random.randint(100, 200),
                random.randint(120, 210),
            ),
        )

    font = _load_font(30)
    spacing = width // (_CAPTCHA_LEN + 1)
    for i, ch in enumerate(text):
        ch_img = Image.new('RGBA', (36, 44), (0, 0, 0, 0))
        ch_draw = ImageDraw.Draw(ch_img)
        color = (
            random.randint(35, 95),
            random.randint(45, 110),
            random.randint(90, 160),
        )
        ch_draw.text((4, 4), ch, font=font, fill=color)
        angle = random.randint(-14, 14)
        ch_img = ch_img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        x = spacing * (i + 1) - ch_img.width // 2
        y = (height - ch_img.height) // 2 + random.randint(-3, 3)
        img.paste(ch_img, (x, y), ch_img)

    # 前景细线（略增机器识别难度）
    for _ in range(2):
        draw.arc(
            [
                random.randint(0, 40),
                random.randint(0, 20),
                random.randint(width - 40, width),
                random.randint(height - 20, height),
            ],
            start=random.randint(0, 180),
            end=random.randint(200, 360),
            fill=(random.randint(140, 190), random.randint(140, 190), random.randint(160, 200)),
            width=1,
        )

    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def issue_login_captcha() -> dict:
    """生成验证码并写入 session，返回 captcha_id 与 base64 图片。"""
    text = _random_text()
    captcha_id = secrets.token_urlsafe(12)
    png = _build_image(text)
    b64 = base64.b64encode(png).decode('ascii')
    session[_SESSION_KEY] = {
        'id': captcha_id,
        'hash': generate_password_hash(text.lower()),
        'exp': (datetime.now() + timedelta(minutes=_CAPTCHA_TTL_MINUTES)).isoformat(),
    }
    session.modified = True
    return {
        'captcha_id': captcha_id,
        'image': f'data:image/png;base64,{b64}',
    }


def verify_login_captcha(captcha_id: str, code: str, *, consume: bool = True) -> tuple[bool, str]:
    """校验图形验证码。consume=True 时无论成败均作废，防止重放。"""
    captcha_id = (captcha_id or '').strip()
    code = (code or '').strip().lower()
    if not captcha_id or not code:
        return False, '请输入图形验证码'
    store = session.get(_SESSION_KEY)
    if not store or store.get('id') != captcha_id:
        return False, '图形验证码已失效，请点击图片刷新'
    try:
        exp = datetime.fromisoformat(store['exp'])
    except (TypeError, ValueError):
        session.pop(_SESSION_KEY, None)
        return False, '图形验证码已失效，请点击图片刷新'
    if datetime.now() > exp:
        session.pop(_SESSION_KEY, None)
        return False, '图形验证码已过期，请点击图片刷新'
    ok_match = check_password_hash(store['hash'], code)
    if consume:
        session.pop(_SESSION_KEY, None)
        session.modified = True
    if not ok_match:
        return False, '图形验证码错误'
    return True, ''


def verify_login_captcha_payload(data: dict, *, consume: bool = True) -> tuple[bool, str]:
    return verify_login_captcha(
        data.get('captcha_id') or '',
        data.get('captcha_code') or data.get('captcha') or '',
        consume=consume,
    )
