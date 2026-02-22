import os
from datetime import timedelta

class Config:
    """Flask アプリケーション設定"""

    # Flask 基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # ファイルアップロード設定
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = int(os.environ.get('CSV_MAX_FILE_SIZE', str(50 * 1024 * 1024)))  # デフォルト50MB
    ALLOWED_EXTENSIONS = {'csv'}

    # Google Sheets API 設定
    SERVICE_ACCOUNT_FILE = os.path.join('config', 'service_account.json')
    SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID') or None

    # マッピング設定
    MAPPING_FILE = os.path.join('data', 'mapping.json')

    # アプリケーション設定
    DEFAULT_YEAR = int(os.environ.get('DEFAULT_YEAR', '2025'))
    CSV_ENCODING = 'Shift_JIS'

    # セッションストア設定
    SESSION_DB_PATH = os.path.join('data', 'sessions', 'sessions.db')
    SESSION_TTL_SECONDS = int(os.environ.get('SESSION_TTL_SECONDS', '1800'))  # 30分
    SESSION_CLEANUP_INTERVAL_HOURS = int(os.environ.get('SESSION_CLEANUP_INTERVAL_HOURS', '6'))  # 6時間

    # API 設定
    API_TIMEOUT = 30
    BATCH_SIZE = 100

    # OpenAI API設定（ChatGPT分類機能 v2.0）
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    GPT_MODEL = os.environ.get('GPT_MODEL', 'gpt-5-mini')
    GPT_MAX_TOKENS = int(os.environ.get('GPT_MAX_TOKENS', '4000'))  # v2.2: gpt-5-mini推論トークン対策（1500→4000、Issue #75 Task9）
    GPT_TEMPERATURE = float(os.environ.get('GPT_TEMPERATURE', '1.0'))  # gpt-5-miniはtemperature=1.0のみサポート
    GPT_BATCH_SIZE = int(os.environ.get('GPT_BATCH_SIZE', '5'))  # v2.2: トークン超過対策（10→5、Issue #75 Task9）
    GPT_BATCH_DELAY_SECONDS = int(os.environ.get('GPT_BATCH_DELAY_SECONDS', '3'))  # バッチ間遅延（秒）
    GPT_MIN_BATCH_SIZE = int(os.environ.get('GPT_MIN_BATCH_SIZE', '1'))  # バッチ分割の最小サイズ（Rate Limit対策）

    # ログ設定
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join('logs', 'app.log')

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
