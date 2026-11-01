import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'phishguard-dev-secret-key-2026-secure-token')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'phishguard.db'))
    
    # Simulation and SMTP configurations
    STRICT_ALLOWLIST = os.environ.get('STRICT_ALLOWLIST', 'true').lower() in ('true', '1', 'yes')
    DEFAULT_ALLOWLIST_DOMAINS = ['company.internal', 'example.com', 'phishguard.test', 'demo.local']
    
    # Local SMTP (Default to Mailpit 127.0.0.1:1025, no TLS, no auth)
    SMTP_ENABLED = os.environ.get('SMTP_ENABLED', 'false').lower() in ('true', '1', 'yes')
    SMTP_HOST = os.environ.get('SMTP_HOST', '127.0.0.1')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 1025))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'false').lower() in ('true', '1', 'yes')
    SMTP_FROM = os.environ.get('SMTP_FROM', 'simulation@phishguard.test')
    
    # App info
    APP_NAME = "PhishGuard"
    APP_VERSION = "2.4.0"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestConfig(Config):
    TESTING = True
    DATABASE_PATH = str(BASE_DIR / 'test_phishguard.db')
    SECRET_KEY = 'test-secret-key'
    STRICT_ALLOWLIST = True
