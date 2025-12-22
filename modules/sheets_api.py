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


# ==================== Phase 2: セル操作 ====================

def get_month_row(month: int) -> int:
    """
    月番号から行番号を計算する

    スプレッドシート構造:
    - 行1: タイトル行
    - 行2: 空行
    - 行3: ヘッダー行
    - 行4～15: 月別データ（1月～12月）

    計算式: row = 3 + month

    Args:
        month: 月番号（1～12）

    Returns:
        int: 行番号（4～15）

    Raises:
        ValueError: 月番号が1～12の範囲外の場合

    Example:
        >>> get_month_row(1)  # 1月
        4
        >>> get_month_row(8)  # 8月
        11
        >>> get_month_row(12)  # 12月
        15
    """
    # 月番号のバリデーション
    if not isinstance(month, int):
        logger.error(f"[ROW:ERROR] 月番号は整数である必要があります: {month}")
        raise ValueError(f"月番号は整数である必要があります: {month}")

    if month < 1 or month > 12:
        logger.error(f"[ROW:ERROR] 月番号が範囲外です: {month}（有効範囲: 1～12）")
        raise ValueError(f"月番号が範囲外です: {month}（有効範囲: 1～12）")

    # 行番号計算
    row = 3 + month

    logger.debug(f"[ROW:CALC] 月={month} -> 行={row}")
    return row


def get_column_index(column_letter: str) -> int:
    """
    列名（A, B, C...）から列番号（1, 2, 3...）を計算する

    有効な列範囲: B～V（支払額～その他カテゴリ）

    Args:
        column_letter: 列名（例: "B", "C", "V"）

    Returns:
        int: 列番号（Bは2、Cは3、Vは22）

    Raises:
        ValueError: 列名が不正な場合（B～V以外、または複数文字）

    Example:
        >>> get_column_index("B")  # 支払額
        2
        >>> get_column_index("C")  # 外食費
        3
        >>> get_column_index("V")  # その他カテゴリ
        22
    """
    # 入力の正規化（大文字変換、strip）
    if not isinstance(column_letter, str):
        logger.error(f"[COL:ERROR] 列名は文字列である必要があります: {column_letter}")
        raise ValueError(f"列名は文字列である必要があります: {column_letter}")

    column_letter = column_letter.strip().upper()

    # 単一文字チェック
    if len(column_letter) != 1:
        logger.error(f"[COL:ERROR] 列名は1文字である必要があります: {column_letter}")
        raise ValueError(f"列名は1文字である必要があります: {column_letter}")

    # 有効列範囲チェック（B～V）
    if column_letter < 'B' or column_letter > 'V':
        logger.error(f"[COL:ERROR] 列名が範囲外です: {column_letter}（有効範囲: B～V）")
        raise ValueError(f"列名が範囲外です: {column_letter}（有効範囲: B～V）")

    # 列番号計算
    column_index = ord(column_letter) - ord('A') + 1

    logger.debug(f"[COL:CALC] 列={column_letter} -> 列番号={column_index}")
    return column_index


def get_cell_value(worksheet: Worksheet, row: int, column: int) -> float:
    """
    指定セルの値を取得する

    Args:
        worksheet: ワークシートオブジェクト
        row: 行番号
        column: 列番号

    Returns:
        float: セルの値（空セルの場合は0.0を返す）

    Raises:
        CellUpdateError: セル値取得に失敗した場合

    Example:
        >>> worksheet = get_year_sheet(spreadsheet, 2025)
        >>> value = get_cell_value(worksheet, 11, 2)  # 8月のB列（支払額）
        >>> print(value)
        12500.0
    """
    try:
        # セル値取得
        cell_value = worksheet.cell(row, column).value

        # 空セル処理（None, "", 空白）
        if cell_value is None or cell_value == "" or (isinstance(cell_value, str) and cell_value.strip() == ""):
            logger.debug(f"[CELL:GET] 行={row}, 列={column}, 値=0.0（空セル）")
            return 0.0

        # 数値変換
        value = float(cell_value)
        logger.debug(f"[CELL:GET] 行={row}, 列={column}, 値={value}")
        return value

    except gspread.exceptions.APIError as e:
        logger.error(f"[CELL:ERROR] セル値取得エラー（API）: 行={row}, 列={column}, エラー={str(e)}")
        raise CellUpdateError(
            f"セル値取得に失敗しました（API）: 行={row}, 列={column}",
            details={'row': row, 'column': column, 'error': str(e)}
        )

    except ValueError as e:
        logger.error(f"[CELL:ERROR] セル値の数値変換に失敗: 行={row}, 列={column}, 値={cell_value}")
        raise CellUpdateError(
            f"セル値の数値変換に失敗しました: 行={row}, 列={column}, 値={cell_value}",
            details={'row': row, 'column': column, 'value': cell_value, 'error': str(e)}
        )

    except Exception as e:
        logger.error(f"[CELL:ERROR] セル値取得エラー: 行={row}, 列={column}, エラー={str(e)}")
        raise CellUpdateError(
            f"セル値取得に失敗しました: 行={row}, 列={column}",
            details={'row': row, 'column': column, 'error': str(e)}
        )


def update_cell_value(
    worksheet: Worksheet,
    row: int,
    column: int,
    amount: float,
    add_mode: bool = True
) -> dict:
    """
    指定セルの値を更新する（加算または上書き）

    Args:
        worksheet: ワークシートオブジェクト
        row: 行番号
        column: 列番号
        amount: 金額
        add_mode: True=加算モード、False=上書きモード（デフォルト: True）

    Returns:
        dict: 更新結果
            {
                'row': int,
                'column': int,
                'old_value': float,
                'new_value': float,
                'added_amount': float
            }

    Raises:
        CellUpdateError: セル更新に失敗した場合

    Example:
        >>> # 加算モード（デフォルト）
        >>> result = update_cell_value(worksheet, 11, 2, 5780.0)
        >>> print(result)
        {'row': 11, 'column': 2, 'old_value': 12500.0, 'new_value': 18280.0, 'added_amount': 5780.0}

        >>> # 上書きモード
        >>> result = update_cell_value(worksheet, 11, 2, 5780.0, add_mode=False)
        >>> print(result)
        {'row': 11, 'column': 2, 'old_value': 12500.0, 'new_value': 5780.0, 'added_amount': 5780.0}
    """
    try:
        # 既存値取得
        old_value = get_cell_value(worksheet, row, column)

        # 新値計算
        if add_mode:
            new_value = old_value + amount
        else:
            new_value = amount

        # セル更新
        worksheet.update_cell(row, column, new_value)

        # ログ記録（監査用）
        mode_str = "加算" if add_mode else "上書き"
        logger.info(
            f"[CELL:UPDATE] セル更新成功（{mode_str}） - "
            f"行={row}, 列={column}, 旧値={old_value}, 新値={new_value}, 加算額={amount}"
        )

        # 結果辞書を作成
        result = {
            'row': row,
            'column': column,
            'old_value': old_value,
            'new_value': new_value,
            'added_amount': amount
        }

        return result

    except CellUpdateError:
        # get_cell_value()からの例外はそのまま再送出
        raise

    except gspread.exceptions.APIError as e:
        logger.error(f"[CELL:ERROR] セル更新エラー（API）: 行={row}, 列={column}, エラー={str(e)}")
        raise CellUpdateError(
            f"セル更新に失敗しました（API）: 行={row}, 列={column}",
            details={'row': row, 'column': column, 'amount': amount, 'error': str(e)}
        )

    except Exception as e:
        logger.error(f"[CELL:ERROR] セル更新エラー: 行={row}, 列={column}, エラー={str(e)}")
        raise CellUpdateError(
            f"セル更新に失敗しました: 行={row}, 列={column}",
            details={'row': row, 'column': column, 'amount': amount, 'error': str(e)}
        )
