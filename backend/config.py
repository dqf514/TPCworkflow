# -*- coding: utf-8 -*-
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
SIGNATURE_DIR = os.path.join(UPLOAD_DIR, 'signatures')
BRANDING_DIR = os.path.join(UPLOAD_DIR, 'branding')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SIGNATURE_DIR, exist_ok=True)
os.makedirs(BRANDING_DIR, exist_ok=True)

_db_path = os.path.join(DATA_DIR, 'tpcworkflow.db').replace('\\', '/')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-change-me-in-production')
    # 生产 HTTPS 反代：.env 设 SESSION_COOKIE_SECURE=1；SECRET_KEY 必须固定且勿用默认值
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in (
        '1',
        'true',
        'yes',
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI',
        f'sqlite:///{_db_path}',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
    }
    UPLOAD_FOLDER = UPLOAD_DIR
    SIGNATURE_FOLDER = SIGNATURE_DIR
    BRANDING_FOLDER = BRANDING_DIR
    DEFAULT_LOCALE = os.environ.get('DEFAULT_LOCALE', 'zh-CN')
    JSON_AS_ASCII = False

    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() not in ('0', 'false')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ('1', 'true')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', '')

    AZURE_TENANT_ID = os.environ.get('AZURE_TENANT_ID', '')
    AZURE_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID', '')
    AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET', '')
    AZURE_REDIRECT_URI = os.environ.get(
        'AZURE_REDIRECT_URI',
        'http://127.0.0.1:5173/auth/azure/callback',
    )
    AZURE_SCOPES = os.environ.get('AZURE_SCOPES', 'openid profile email')

    PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', 'http://127.0.0.1:5173')

    # Windows 桌面客户端安装包（默认项目 deploy/downloads/TPCWorkflow.Client.exe）
    CLIENT_DOWNLOAD_FILE = os.environ.get(
        'CLIENT_DOWNLOAD_FILE',
        os.path.join(PROJECT_ROOT, 'deploy', 'downloads', 'TPCWorkflow.Client.exe'),
    )

    # 客户端版本（client-version.json 缺失时的回退值）
    CLIENT_APP_VERSION = os.environ.get('CLIENT_APP_VERSION', '1.0.0')
    CLIENT_VERSION_FILE = os.environ.get(
        'CLIENT_VERSION_FILE',
        os.path.join(PROJECT_ROOT, 'deploy', 'downloads', 'client-version.json'),
    )
