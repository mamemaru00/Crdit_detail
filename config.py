import os
from datetime import timedelta

class Config:
    """Flask アプリケーション設定"""

    # Flask 基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # ファイルアップロード設定
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'csv'}

    # Google Sheets API 設定
    SERVICE_ACCOUNT_FILE = os.path.join('config', 'service_account.json')
    SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID') or None

    # マッピング設定
    MAPPING_FILE = os.path.join('config', 'mapping.json')

    # アプリケーション設定
    DEFAULT_YEAR = 2025
    DEFAULT_COLUMN = 'B'
    CSV_ENCODING = 'Shift_JIS'

    # API 設定
    API_TIMEOUT = 30
    BATCH_SIZE = 100

    # ログ設定
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'

    # セキュリティ設定
    AUTO_DELETE_UPLOADS = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # ローカル環境のためFalse（本番環境ではTrue）
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # 本番環境ではHTTPSを想定

class TestingConfig(Config):
    """テスト環境設定"""
    TESTING = True
    WTF_CSRF_ENABLED = False

# 環境別設定の辞書
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
