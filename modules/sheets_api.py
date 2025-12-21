"""
Google Sheets API連携モジュール

このモジュールはGoogle Sheets APIとの認証・接続・読み書き・バッチ更新を行います。

主な機能:
- サービスアカウント認証（gspread + google-auth）
- スプレッドシート接続・年シート取得
- セル値の読み取り・加算・更新
- バッチ更新によるAPIコール数削減
- APIレート制限対応（リトライ処理）

使用例:
    # 1. 認証
    >>> client = authenticate()

    # 2. スプレッドシート接続
    >>> spreadsheet = open_spreadsheet(client, "your-spreadsheet-id")

    # 3. 年シート取得
    >>> worksheet = get_year_sheet(spreadsheet, 2025)

    # 4. セル更新
    >>> row = get_month_row(8)  # 8月 → 11行目
    >>> col = get_column_index('C')  # C列 → 3
    >>> new_value = update_cell_value(worksheet, row, col, 5780)
"""

import logging
from typing import Optional, Any
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from gspread import Spreadsheet, Worksheet

# ==================== ロガー設定 ====================

logger = logging.getLogger(__name__)


# ==================== 定数定義 ====================

# ファイルパス
DEFAULT_CREDENTIALS_PATH = Path("config/service_account.json")

# Google Sheets APIスコープ
SPREADSHEET_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets'
]

# APIレート制限対応
RATE_LIMIT_WAIT = 1.0  # API呼び出し間の待機秒数（秒）
MAX_RETRIES = 3  # 最大リトライ回数

# バッチ更新
MAX_BATCH_SIZE = 100  # バッチ更新の最大サイズ


# ==================== カスタム例外クラス ====================

class SheetsAPIError(Exception):
    """Google Sheets API操作のエラー基底クラス

    すべてのSheets API関連例外の基底クラスです。
    エラーメッセージと詳細情報を保持します。

    Attributes:
        message (str): エラーメッセージ
        details (dict): エラーの詳細情報(オプション)
    """

    def __init__(self, message: str, details: Optional[dict] = None):
        """
        Args:
            message (str): エラーメッセージ
            details (Optional[dict]): エラーの詳細情報。デフォルトは空の辞書
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(SheetsAPIError):
    """認証エラー

    サービスアカウント認証に失敗した場合に発生します。
    認証情報ファイルの不存在、JSON解析エラー、認証失敗時に使用されます。
    """
    pass


class SpreadsheetNotFoundError(SheetsAPIError):
    """スプレッドシート未検出エラー

    指定されたIDのスプレッドシートが存在しない、または
    アクセス権限がない場合に発生します。
    """
    pass


class SheetNotFoundError(SheetsAPIError):
    """シート未検出エラー

    指定された年のシート（例："2025年"）が存在しない場合に発生します。
    """
    pass


class CellUpdateError(SheetsAPIError):
    """セル更新エラー

    セルの読み取りまたは更新処理が失敗した場合に発生します。
    APIエラー、ネットワークエラー、レート制限超過時に使用されます。
    """
    pass


# ==================== Phase 1: 基盤実装 ====================

def authenticate(credentials_path: Optional[Path] = None) -> gspread.Client:
    """
    サービスアカウントでGoogle Sheets APIに認証する

    Args:
        credentials_path: 認証情報ファイルのパス（デフォルト: config/service_account.json）

    Returns:
        gspread.Client: 認証済みのgspreadクライアント

    Raises:
        AuthenticationError: 認証に失敗した場合

    Example:
        >>> client = authenticate()
        >>> client = authenticate(Path("path/to/service_account.json"))
    """
    # デフォルトパス設定
    if credentials_path is None:
        credentials_path = DEFAULT_CREDENTIALS_PATH

    # ファイル存在確認
    if not credentials_path.exists():
        logger.error(f"[AUTH:ERROR] 認証情報ファイルが見つかりません: {credentials_path}")
        raise AuthenticationError(
            f"認証情報ファイルが見つかりません: {credentials_path}",
            details={'path': str(credentials_path)}
        )

    if not credentials_path.is_file():
        logger.error(f"[AUTH:ERROR] 指定されたパスはファイルではありません: {credentials_path}")
        raise AuthenticationError(
            f"指定されたパスはファイルではありません: {credentials_path}",
            details={'path': str(credentials_path)}
        )

    try:
        # 認証情報読み込み
        creds = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=SPREADSHEET_SCOPES
        )

        # gspreadクライアント生成
        client = gspread.authorize(creds)

        logger.info(f"[AUTH:SUCCESS] 認証成功: {credentials_path}")
        return client

    except FileNotFoundError as e:
        logger.error(f"[AUTH:ERROR] 認証情報ファイルが見つかりません: {str(e)}")
        raise AuthenticationError(
            f"認証情報ファイルが見つかりません: {str(e)}",
            details={'path': str(credentials_path), 'error': str(e)}
        )

    except ValueError as e:
        # JSON解析エラー
        logger.error(f"[AUTH:ERROR] 認証情報ファイルのJSON解析に失敗しました: {str(e)}")
        raise AuthenticationError(
            f"認証情報ファイルのJSON解析に失敗しました: {str(e)}",
            details={'path': str(credentials_path), 'error': str(e)}
        )

    except Exception as e:
        # その他の認証エラー
        logger.error(f"[AUTH:ERROR] 認証に失敗しました: {str(e)}")
        raise AuthenticationError(
            f"認証に失敗しました: {str(e)}",
            details={'path': str(credentials_path), 'error': str(e)}
        )


def open_spreadsheet(client: gspread.Client, spreadsheet_id: str) -> Spreadsheet:
    """
    スプレッドシートを開く

    Args:
        client: 認証済みのgspreadクライアント
        spreadsheet_id: スプレッドシートID

    Returns:
        Spreadsheet: スプレッドシートオブジェクト

    Raises:
        SpreadsheetNotFoundError: スプレッドシートが見つからない場合

    Example:
        >>> client = authenticate()
        >>> sheet = open_spreadsheet(client, "1A2B3C...")
    """
    try:
        # スプレッドシート取得
        spreadsheet = client.open_by_key(spreadsheet_id)

        logger.info(f"[SHEET:OPEN] スプレッドシート接続: ID={spreadsheet_id}, "
                   f"タイトル='{spreadsheet.title}'")
        return spreadsheet

    except gspread.exceptions.SpreadsheetNotFound as e:
        logger.error(f"[SHEET:ERROR] スプレッドシートが見つかりません: ID={spreadsheet_id}")
        raise SpreadsheetNotFoundError(
            f"スプレッドシートが見つかりません: ID={spreadsheet_id}",
            details={'spreadsheet_id': spreadsheet_id, 'error': str(e)}
        )

    except gspread.exceptions.APIError as e:
        logger.error(f"[SHEET:ERROR] API接続エラー: {str(e)}")
        raise SpreadsheetNotFoundError(
            f"スプレッドシートへのアクセスに失敗しました: {str(e)}",
            details={'spreadsheet_id': spreadsheet_id, 'error': str(e)}
        )

    except Exception as e:
        logger.error(f"[SHEET:ERROR] スプレッドシート接続エラー: {str(e)}")
        raise SpreadsheetNotFoundError(
            f"スプレッドシートの接続に失敗しました: {str(e)}",
            details={'spreadsheet_id': spreadsheet_id, 'error': str(e)}
        )


def get_year_sheet(spreadsheet: Spreadsheet, year: int) -> Worksheet:
    """
    年別シートを取得する

    Args:
        spreadsheet: スプレッドシートオブジェクト
        year: 取得する年（例: 2025）

    Returns:
        Worksheet: 年別ワークシート

    Raises:
        SheetNotFoundError: 年別シートが見つからない場合

    Example:
        >>> sheet = get_year_sheet(spreadsheet, 2025)
    """
    # シート名を生成
    sheet_name = f"{year}年"

    try:
        # シート取得
        worksheet = spreadsheet.worksheet(sheet_name)

        logger.info(f"[SHEET:GET] 年シート取得: {sheet_name}")
        return worksheet

    except gspread.exceptions.WorksheetNotFound as e:
        logger.error(f"[SHEET:ERROR] 年シートが見つかりません: {sheet_name}")
        raise SheetNotFoundError(
            f"年シートが見つかりません: {sheet_name}",
            details={'year': year, 'sheet_name': sheet_name, 'error': str(e)}
        )

    except Exception as e:
        logger.error(f"[SHEET:ERROR] 年シート取得エラー: {str(e)}")
        raise SheetNotFoundError(
            f"年シートの取得に失敗しました: {str(e)}",
            details={'year': year, 'sheet_name': sheet_name, 'error': str(e)}
        )
