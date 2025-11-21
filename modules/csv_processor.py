"""
イオンカード明細CSV処理モジュール

このモジュールはイオンカード利用明細CSVファイルを処理し、
必要なデータを抽出・変換する機能を提供します。

主な機能:
- CSVファイルの読み込み(Shift_JIS → UTF-8変換、CP932フォールバック対応)
- 明細データの抽出(8行目以降、6桁数字で始まる行)
- 全フィールドの抽出(date, user, store, payment_method, amount, note)
- 日付変換(YYMMDD → YYYY/MM/DD)
- プレビューデータの生成
- ファイルパス検証(パストラバーサル対策)
"""

import pandas as pd
import chardet
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path


# ==================== 定数定義 ====================

ENCODING_DETECTION_BYTES = 10000  # エンコーディング検出に使用するバイト数
PREVIEW_ROWS = 5  # プレビュー表示行数
DETAIL_START_ROW = 8  # 明細データ開始行(0インデックス)
DATE_PATTERN = r'^\d{6}$'  # 6桁数字パターン(YYMMDD)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 最大ファイルサイズ 10MB


# ==================== カスタム例外クラス ====================

class CSVProcessingError(Exception):
    """CSV処理の基底例外クラス

    すべてのCSV処理関連例外の基底クラスです。
    エラーメッセージと詳細情報を保持します。

    Attributes:
        message (str): エラーメッセージ
        details (Dict): エラーの詳細情報(オプション)
    """

    def __init__(self, message: str, details: Optional[Dict] = None):
        """
        Args:
            message (str): エラーメッセージ
            details (Optional[Dict]): エラーの詳細情報。デフォルトは空の辞書
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EncodingDetectionError(CSVProcessingError):
    """エンコーディング検出エラー

    ファイルの文字エンコーディングを検出できなかった場合に発生します。
    chardetでの検出失敗やCP932フォールバックの失敗時に使用されます。
    """
    pass


class InvalidFileFormatError(CSVProcessingError):
    """無効なファイル形式エラー

    CSVファイルのフォーマットが期待される形式と異なる場合や
    ファイルサイズが制限を超えている場合に発生します。
    """
    pass


class DateConversionError(CSVProcessingError):
    """日付変換エラー

    YYMMDD形式の日付をYYYY/MM/DD形式に変換する際に
    無効な日付形式や値が検出された場合に発生します。
    """
    pass


class DataExtractionError(CSVProcessingError):
    """データ抽出エラー

    CSVファイルから明細データを抽出する際に
    必要なフィールドが不足している場合や
    データが期待される形式でない場合に発生します。
    """
    pass


class PathValidationError(CSVProcessingError):
    """ファイルパス検証エラー(パストラバーサル対策)

    ファイルパスが許可されたディレクトリ外を指している場合や
    パストラバーサル攻撃の可能性が検出された場合に発生します。
    """
    pass


# ==================== セキュリティ関数 ====================

def validate_file_path(file_path: str, allowed_dir: str) -> bool:
    """ファイルパスの妥当性を検証(パストラバーサル攻撃防止)

    指定されたファイルパスが許可されたディレクトリ配下にあることを確認します。
    パスを正規化してシンボリックリンクを解決し、絶対パスで比較します。

    Args:
        file_path (str): 検証対象のファイルパス
        allowed_dir (str): 許可されたディレクトリパス

    Returns:
        bool: パスが有効な場合True

    Raises:
        PathValidationError: パスが許可されたディレクトリ外の場合

    Example:
        >>> validate_file_path('/tmp/uploads/file.csv', '/tmp/uploads')
        True
        >>> validate_file_path('/tmp/../etc/passwd', '/tmp/uploads')
        PathValidationError: ファイルパスが許可されたディレクトリ外です
    """
    # パスを正規化して絶対パスに変換(シンボリックリンク解決)
    normalized_file_path = Path(file_path).resolve()
    normalized_allowed_dir = Path(allowed_dir).resolve()

    # 許可されたディレクトリ配下にあるか確認
    try:
        # relative_to()が例外を発生させない場合、配下にあることを意味する
        normalized_file_path.relative_to(normalized_allowed_dir)
        return True
    except ValueError:
        # relative_to()が失敗した場合、許可されたディレクトリ外
        raise PathValidationError(
            f"ファイルパスが許可されたディレクトリ外です: {file_path}",
            details={
                "file_path": str(normalized_file_path),
                "allowed_dir": str(normalized_allowed_dir)
            }
        )


def validate_file_size(file_path: str) -> bool:
    """ファイルサイズの妥当性を検証(DoS攻撃防止)

    指定されたファイルのサイズが最大許容サイズ(10MB)を超えていないか確認します。
    大容量ファイルによるDoS攻撃を防止します。

    Args:
        file_path (str): 検証対象のファイルパス

    Returns:
        bool: ファイルサイズが許容範囲内の場合True

    Raises:
        InvalidFileFormatError: ファイルサイズが制限を超えている場合
        FileNotFoundError: ファイルが存在しない場合

    Example:
        >>> validate_file_size('/tmp/uploads/small.csv')
        True
        >>> validate_file_size('/tmp/uploads/huge.csv')
        InvalidFileFormatError: ファイルサイズが制限を超えています
    """
    path = Path(file_path)

    # ファイルの存在確認
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    # ファイルサイズ取得
    file_size = path.stat().st_size

    # サイズ制限チェック
    if file_size > MAX_FILE_SIZE:
        file_size_mb = file_size / (1024 * 1024)
        max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise InvalidFileFormatError(
            f"ファイルサイズが制限を超えています: {file_size_mb:.2f}MB (制限: {max_size_mb:.0f}MB)",
            details={
                "file_size_bytes": file_size,
                "file_size_mb": file_size_mb,
                "max_size_mb": max_size_mb
            }
        )

    return True


# ==================== エンコーディング検出関数 ====================

def detect_encoding(file_path: str) -> str:
    """ファイルのエンコーディングを自動検出(CP932フォールバック対応)

    chardetライブラリを使用してファイルのエンコーディングを検出します。
    信頼度が低い場合やShift_JIS検出時は、Windows環境対応のため
    CP932での読み込みを試行します。

    検出ロジック:
    1. ファイルの先頭10000バイトを読み込み
    2. chardet.detect()でエンコーディングを検出
    3. 信頼度が0.7未満の場合、CP932で読み込みを試行
    4. Shift_JIS検出時も、CP932で読み込みを試行(特殊文字対応)
    5. CP932が成功したら'cp932'を返す
    6. 失敗したら検出されたエンコーディングまたはエラーを返す

    Args:
        file_path (str): 検出対象のファイルパス

    Returns:
        str: 検出されたエンコーディング名(小文字)

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        EncodingDetectionError: エンコーディング検出に失敗した場合

    Example:
        >>> detect_encoding('/tmp/sjis.csv')
        'cp932'
        >>> detect_encoding('/tmp/utf8.csv')
        'utf-8'

    Note:
        CP932フォールバックは、Windowsで作成された特殊文字
        (髙、﨑、①、②など)を含むファイルに対応するために必要です。
    """
    path = Path(file_path)

    # ファイルの存在確認
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    try:
        # ファイルの先頭部分を読み込み
        with open(file_path, 'rb') as f:
            raw_data = f.read(ENCODING_DETECTION_BYTES)

        # chardetでエンコーディング検出
        detection_result = chardet.detect(raw_data)
        detected_encoding = detection_result.get('encoding')
        confidence = detection_result.get('confidence', 0)

        # 検出結果がNoneの場合
        if detected_encoding is None:
            # CP932で読み込みを試行
            try:
                with open(file_path, 'r', encoding='cp932') as f:
                    f.read(1024)  # 少量読み込んで検証
                return 'cp932'
            except (UnicodeDecodeError, LookupError):
                raise EncodingDetectionError(
                    "エンコーディングを検出できませんでした",
                    details={
                        "file_path": file_path,
                        "detection_result": detection_result
                    }
                )

        # エンコーディング名を小文字に変換
        encoding_lower = detected_encoding.lower()

        # 信頼度が低い場合、CP932で読み込みを試行
        if confidence < 0.7:
            try:
                with open(file_path, 'r', encoding='cp932') as f:
                    f.read(1024)  # 少量読み込んで検証
                return 'cp932'
            except (UnicodeDecodeError, LookupError):
                # CP932で失敗した場合は検出されたエンコーディングを返す
                pass

        # Shift_JIS検出時は、CP932での読み込みを試行(Windows環境対応)
        if 'shift_jis' in encoding_lower or 'shiftjis' in encoding_lower:
            try:
                with open(file_path, 'r', encoding='cp932') as f:
                    f.read(1024)  # 少量読み込んで検証
                return 'cp932'
            except (UnicodeDecodeError, LookupError):
                # CP932で失敗した場合は'shift_jis'を返す
                return 'shift_jis'

        return encoding_lower

    except Exception as e:
        if isinstance(e, (FileNotFoundError, EncodingDetectionError)):
            raise
        raise EncodingDetectionError(
            f"エンコーディング検出中にエラーが発生しました: {str(e)}",
            details={
                "file_path": file_path,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )


# ==================== CSV読み込み関数 ====================

def read_csv_file(file_path: str) -> pd.DataFrame:
    """CSVファイルを読み込み、DataFrameに変換(CP932対応)

    ファイルのエンコーディングを自動検出してCSVファイルを読み込みます。
    すべての列を文字列型として読み込み、ヘッダー行は無視します。

    処理フロー:
    1. detect_encoding()でエンコーディングを検出
    2. pandas.read_csv()で読み込み(全列文字列型、ヘッダーなし)
    3. DataFrameが空でないことを確認

    Args:
        file_path (str): 読み込み対象のCSVファイルパス

    Returns:
        pd.DataFrame: 読み込まれたDataFrame(全列文字列型)

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        InvalidFileFormatError: CSV読み込みエラーまたは空ファイルの場合
        EncodingDetectionError: エンコーディング検出エラー

    Example:
        >>> df = read_csv_file('/tmp/aeon_card.csv')
        >>> type(df)
        <class 'pandas.core.frame.DataFrame'>
        >>> df[0].dtype
        dtype('O')  # object型(文字列)

    Note:
        - すべての列をobject型(文字列)として読み込み、後続処理で変換
        - エンコーディング検出エラーは自動的に伝播
    """
    # エンコーディング検出
    encoding = detect_encoding(file_path)

    try:
        # CSVファイルを読み込み
        df = pd.read_csv(
            file_path,
            encoding=encoding,
            header=None,  # ヘッダー行なし
            dtype=str  # 全列を文字列として読み込み
        )

        # DataFrameが空でないことを確認
        if df.empty:
            raise InvalidFileFormatError(
                "CSVファイルが空です",
                details={
                    "file_path": file_path,
                    "encoding": encoding
                }
            )

        return df

    except UnicodeDecodeError as e:
        raise InvalidFileFormatError(
            f"CSVファイルの読み込みに失敗しました(エンコーディングエラー): {str(e)}",
            details={
                "file_path": file_path,
                "encoding": encoding,
                "error_type": "UnicodeDecodeError",
                "error_message": str(e)
            }
        )
    except pd.errors.ParserError as e:
        raise InvalidFileFormatError(
            f"CSVファイルの解析に失敗しました(フォーマットエラー): {str(e)}",
            details={
                "file_path": file_path,
                "encoding": encoding,
                "error_type": "ParserError",
                "error_message": str(e)
            }
        )
    except Exception as e:
        if isinstance(e, InvalidFileFormatError):
            raise
        raise InvalidFileFormatError(
            f"CSVファイルの読み込み中にエラーが発生しました: {str(e)}",
            details={
                "file_path": file_path,
                "encoding": encoding,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )


def is_detail_row(row: pd.Series) -> bool:
    """行が明細行かどうかを判定

    行の最初の列(列0)が6桁数字(YYMMDD形式)であるかを判定します。
    None, NaN, 空文字列の場合はFalseを返します。

    判定ロジック:
    1. row[0]が存在するか確認
    2. pd.isna()でNone/NaNをチェック
    3. 文字列に変換してstrip()
    4. 正規表現DATE_PATTERNにマッチするか判定

    Args:
        row (pd.Series): 判定対象の行データ

    Returns:
        bool: 明細行の場合True、それ以外False

    Example:
        >>> row1 = pd.Series(['250815', '本人', 'ストア名'])
        >>> is_detail_row(row1)
        True
        >>> row2 = pd.Series(['利用日', '利用者', '利用先'])
        >>> is_detail_row(row2)
        False
        >>> row3 = pd.Series([None, '', ''])
        >>> is_detail_row(row3)
        False

    Note:
        - DATE_PATTERN = r'^\d{6}$' (6桁数字)
        - 空白の前後も除去して判定
    """
    # 列0が存在しない場合
    if len(row) == 0 or 0 not in row.index:
        return False

    # 列0の値を取得
    value = row[0]

    # None や NaN の場合
    if pd.isna(value):
        return False

    # 文字列に変換して前後の空白を除去
    value_str = str(value).strip()

    # 空文字列の場合
    if not value_str:
        return False

    # 正規表現で6桁数字かどうか判定
    return bool(re.match(DATE_PATTERN, value_str))


def extract_detail_data(df: pd.DataFrame) -> pd.DataFrame:
    """8行目以降の明細データを抽出し、全6フィールドを取得

    CSVファイルの8行目(インデックス7)以降から明細行を抽出し、
    必要な6つのフィールド(date, user, store, payment_method, amount, note)を
    含むDataFrameを返します。

    処理フロー:
    1. df.iloc[DETAIL_START_ROW:]で8行目以降を取得
    2. is_detail_row()で明細行をフィルタリング
    3. 必要な列(0, 1, 2, 3, 6, 7または8)の存在を確認
    4. 金額列(列6)のカンマを除去
    5. 列名を変更(date, user, store, payment_method, amount, note)

    Args:
        df (pd.DataFrame): 読み込まれたCSVのDataFrame

    Returns:
        pd.DataFrame: 抽出された明細データ(6列)
            - date: 利用日(YYMMDD形式の文字列)
            - user: 利用者区分
            - store: 店舗名
            - payment_method: 支払方法
            - amount: 利用金額(カンマ除去済み文字列)
            - note: 備考

    Raises:
        DataExtractionError: 以下の場合に発生
            - 必要な列が存在しない
            - 明細行が0件
            - 金額列が数値変換できない

    Example:
        >>> df = read_csv_file('/tmp/aeon_card.csv')
        >>> detail_df = extract_detail_data(df)
        >>> detail_df.columns.tolist()
        ['date', 'user', 'store', 'payment_method', 'amount', 'note']
        >>> detail_df.shape
        (150, 6)  # 150件の明細、6列

    Note:
        - DETAIL_START_ROW = 8 (0インデックスなので8行目以降)
        - 備考フィールドは列7または列8から取得(存在しない場合は空文字列)
        - 金額列のカンマ(半角・全角)を除去
    """
    # 8行目以降を取得
    if len(df) <= DETAIL_START_ROW:
        raise DataExtractionError(
            "CSVファイルに明細データが含まれていません(8行目以降がありません)",
            details={
                "total_rows": len(df),
                "detail_start_row": DETAIL_START_ROW
            }
        )

    df_from_detail = df.iloc[DETAIL_START_ROW:]

    # 明細行をフィルタリング
    df_filtered = df_from_detail[df_from_detail.apply(is_detail_row, axis=1)]

    # 明細行が0件の場合
    if df_filtered.empty:
        raise DataExtractionError(
            "明細行が見つかりませんでした(6桁数字で始まる行が存在しません)",
            details={
                "rows_scanned": len(df_from_detail),
                "detail_rows_found": 0
            }
        )

    # 必要な列が存在することを確認
    required_columns = [0, 1, 2, 3, 6]
    missing_columns = [col for col in required_columns if col not in df_filtered.columns]

    if missing_columns:
        raise DataExtractionError(
            f"必要な列が存在しません: {missing_columns}",
            details={
                "missing_columns": missing_columns,
                "available_columns": df_filtered.columns.tolist(),
                "required_columns": required_columns
            }
        )

    # 基本フィールド(列0, 1, 2, 3, 6)を抽出
    detail_df = df_filtered[[0, 1, 2, 3, 6]].copy()

    # 備考フィールド(列7または8)を条件付きで追加
    if 7 in df_filtered.columns:
        detail_df['note_temp'] = df_filtered[7]
    elif 8 in df_filtered.columns:
        detail_df['note_temp'] = df_filtered[8]
    else:
        detail_df['note_temp'] = ""

    # 金額列(インデックス6)のカンマを除去
    detail_df.loc[:, 6] = detail_df[6].str.replace(',', '', regex=False).str.replace('、', '', regex=False)

    # 金額が数値に変換可能か検証
    try:
        # 一時的にfloat変換して検証(実際の変換は後続処理で行う)
        pd.to_numeric(detail_df[6], errors='raise')
    except (ValueError, TypeError) as e:
        # 変換できない値を特定
        invalid_values = detail_df[~detail_df[6].str.match(r'^-?\d+(\.\d+)?$', na=False)][6].unique()
        raise DataExtractionError(
            f"金額列に数値変換できない値が含まれています: {invalid_values.tolist()}",
            details={
                "invalid_values": invalid_values.tolist(),
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )

    # 列名を変更
    detail_df.columns = ['date', 'user', 'store', 'payment_method', 'amount', 'note']

    return detail_df


# ==================== 日付変換関数 ====================

def convert_date_format(yymmdd_str: str) -> str:
    """YYMMDD形式をYYYY/MM/DD形式に変換

    6桁の日付文字列(YYMMDD)をYYYY/MM/DD形式に変換します。
    年の判定ロジック:
    - 00-49 → 2000年代(2000-2049)
    - 50-99 → 1900年代(1950-1999)

    Args:
        yymmdd_str (str): 6桁の日付文字列(例: "250115")

    Returns:
        str: YYYY/MM/DD形式の日付文字列(例: "2025/01/15")

    Raises:
        DateConversionError: 以下の場合に発生
            - 6桁数字でない場合
            - 月が1-12の範囲外
            - 日が1-31の範囲外

    Example:
        >>> convert_date_format("250115")
        '2025/01/15'
        >>> convert_date_format("240229")
        '2024/02/29'
        >>> convert_date_format("000101")
        '2000/01/01'
        >>> convert_date_format("491231")
        '2049/12/31'
        >>> convert_date_format("500101")
        '1950/01/01'
        >>> convert_date_format("991231")
        '1999/12/31'
        >>> convert_date_format("25011")
        DateConversionError: 日付は6桁の数字である必要があります
        >>> convert_date_format("251301")
        DateConversionError: 月は1-12の範囲である必要があります

    Note:
        - 日付の妥当性チェックは簡易版(月:1-12, 日:1-31)
        - 2月29日など詳細な暦チェックは行わない
    """
    # 6桁数字のパターンマッチ
    if not re.match(DATE_PATTERN, yymmdd_str):
        raise DateConversionError(
            f"日付は6桁の数字である必要があります: {yymmdd_str}",
            details={
                "input": yymmdd_str,
                "expected_pattern": "YYMMDD (6桁数字)"
            }
        )

    # YY, MM, DDを抽出
    yy = int(yymmdd_str[0:2])
    mm = int(yymmdd_str[2:4])
    dd = int(yymmdd_str[4:6])

    # 月の妥当性チェック(1-12)
    if mm < 1 or mm > 12:
        raise DateConversionError(
            f"月は1-12の範囲である必要があります: {mm}",
            details={
                "input": yymmdd_str,
                "extracted_month": mm
            }
        )

    # 日の妥当性チェック(1-31)
    if dd < 1 or dd > 31:
        raise DateConversionError(
            f"日は1-31の範囲である必要があります: {dd}",
            details={
                "input": yymmdd_str,
                "extracted_day": dd
            }
        )

    # 年の判定(00-49 → 2000年代, 50-99 → 1900年代)
    if yy <= 49:
        yyyy = 2000 + yy
    else:
        yyyy = 1900 + yy

    # YYYY/MM/DD形式に変換
    return f"{yyyy:04d}/{mm:02d}/{dd:02d}"


def extract_month_number(yymmdd_str: str) -> int:
    """YYMMDD形式から月番号(1-12)を抽出

    6桁の日付文字列(YYMMDD)から月番号を抽出します。

    Args:
        yymmdd_str (str): 6桁の日付文字列(例: "250115")

    Returns:
        int: 月番号(1-12の整数、例: 1)

    Raises:
        DateConversionError: 以下の場合に発生
            - 6桁数字でない場合
            - 月が1-12の範囲外

    Example:
        >>> extract_month_number("250115")
        1
        >>> extract_month_number("241231")
        12
        >>> extract_month_number("250601")
        6
        >>> extract_month_number("25011")
        DateConversionError: 日付は6桁の数字である必要があります
        >>> extract_month_number("251301")
        DateConversionError: 月は1-12の範囲である必要があります

    Note:
        - 日付の妥当性チェックは月部分のみ(1-12)
        - 年や日の妥当性はチェックしない
    """
    # 6桁数字のパターンマッチ
    if not re.match(DATE_PATTERN, yymmdd_str):
        raise DateConversionError(
            f"日付は6桁の数字である必要があります: {yymmdd_str}",
            details={
                "input": yymmdd_str,
                "expected_pattern": "YYMMDD (6桁数字)"
            }
        )

    # MMを抽出
    mm = int(yymmdd_str[2:4])

    # 月の妥当性チェック(1-12)
    if mm < 1 or mm > 12:
        raise DateConversionError(
            f"月は1-12の範囲である必要があります: {mm}",
            details={
                "input": yymmdd_str,
                "extracted_month": mm
            }
        )

    return mm


# ==================== プレビュー生成関数 ====================

def generate_preview(detail_data: List[Dict]) -> List[Dict]:
    """明細データの先頭5件をプレビューとして返す

    明細データリストから先頭5件(または5件未満の場合は全件)を抽出し、
    プレビューデータとして返します。

    Args:
        detail_data (List[Dict]): 明細データのリスト
            各要素は以下のキーを含む辞書:
            - date (str): YYYY/MM/DD形式の日付
            - year (int): 年
            - month (int): 月番号(1-12)
            - month_str (str): 月表示(例: "2025年8月")
            - store (str): 店舗名
            - amount (int): 金額
            - user (str): 利用者区分
            - payment_method (str): 支払方法
            - note (str): 備考

    Returns:
        List[Dict]: 先頭5件のプレビューデータ(5件未満の場合は全件)

    Example:
        >>> detail_data = [
        ...     {'date': '2025/01/15', 'store': 'イオン', 'amount': 5280, ...},
        ...     {'date': '2025/01/16', 'store': 'セブンイレブン', 'amount': 1200, ...},
        ...     # ... 全10件
        ... ]
        >>> preview = generate_preview(detail_data)
        >>> len(preview)
        5
        >>> detail_data_small = [
        ...     {'date': '2025/01/15', 'store': 'イオン', 'amount': 5280, ...},
        ...     {'date': '2025/01/16', 'store': 'セブンイレブン', 'amount': 1200, ...}
        ... ]
        >>> preview_small = generate_preview(detail_data_small)
        >>> len(preview_small)
        2
        >>> empty_data = []
        >>> generate_preview(empty_data)
        []

    Note:
        - PREVIEW_ROWS = 5 が定数として定義済み
        - 空リストの場合も空リストを返す
        - 入力データの変更は行わない(スライスで新しいリストを返す)
    """
    return detail_data[:PREVIEW_ROWS]


# ==================== CSV統合処理関数 ====================

def process_csv_file(file_path: str, allowed_dir: str = '/tmp/uploads') -> Dict:
    """CSV全体処理の統合関数(全フィールド対応)

    CSVファイルの読み込みから明細データ抽出、プレビュー生成、
    サマリー計算までを統合的に処理します。

    処理フロー:
    1. validate_file_path() - ファイルパス検証(パストラバーサル対策)
    2. validate_file_size() - ファイルサイズ検証(DoS攻撃防止)
    3. read_csv_file() - CSV読み込み(エンコーディング自動検出)
    4. extract_detail_data() - 明細データ抽出(全6フィールド)
    5. DataFrameをリスト形式に変換
    6. 各レコードに追加フィールドを設定:
       - year: int - 年(dateから抽出)
       - month: int - 月番号(dateから抽出)
       - month_str: str - 月表示(例: "2025年8月")
       - amount: int - 金額を文字列からintに変換
       - date: str - YYMMDD形式からYYYY/MM/DD形式に変換
    7. generate_preview() - プレビュー生成
    8. サマリー情報の計算

    Args:
        file_path (str): 処理対象のCSVファイルパス
        allowed_dir (str): 許可されたディレクトリパス(デフォルト: '/tmp/uploads')

    Returns:
        Dict: 処理結果を含む辞書
            {
                'details': List[Dict],  # 全明細データ(全フィールド含む)
                'preview': List[Dict],  # プレビューデータ(先頭5件)
                'total_count': int,     # 総件数
                'summary': {
                    'total_amount': int,
                    'date_range': {
                        'start': str,   # YYYY/MM/DD形式
                        'end': str      # YYYY/MM/DD形式
                    }
                }
            }

    Raises:
        PathValidationError: ファイルパスが許可されたディレクトリ外の場合
        InvalidFileFormatError: ファイルサイズ超過またはCSV読み込みエラー
        EncodingDetectionError: エンコーディング検出エラー
        DataExtractionError: 明細データ抽出エラー
        DateConversionError: 日付変換エラー
        CSVProcessingError: その他の予期しないエラー

    Example:
        >>> result = process_csv_file('/tmp/uploads/aeon_card.csv')
        >>> result['total_count']
        150
        >>> result['summary']['total_amount']
        1234567
        >>> result['summary']['date_range']['start']
        '2025/01/01'
        >>> result['summary']['date_range']['end']
        '2025/01/31'
        >>> len(result['details'])
        150
        >>> len(result['preview'])
        5
        >>> result['details'][0].keys()
        dict_keys(['date', 'user', 'store', 'payment_method', 'amount', 'note',
                   'year', 'month', 'month_str'])

    Note:
        - 日付変換: dateフィールドはYYMMDD形式(例: "250115")で保存されているので、
                   convert_date_format()を使用してYYYY/MM/DD形式(例: "2025/01/15")に変換
        - 金額変換: amountフィールドは文字列(例: "5280")なので、intに変換
        - year/month抽出: 変換後のdate(YYYY/MM/DD形式)を'/'で分割して抽出
        - month_str生成: f"{year}年{month}月" 形式で生成
        - エラーは適切な例外クラスで発生し、呼び出し側でハンドリング可能
    """
    try:
        # 1. ファイルパス検証
        validate_file_path(file_path, allowed_dir)

        # 2. ファイルサイズ検証
        validate_file_size(file_path)

        # 3. CSV読み込み
        df = read_csv_file(file_path)

        # 4. 明細データ抽出
        detail_df = extract_detail_data(df)

        # 5. DataFrameをリスト形式に変換
        details = detail_df.to_dict('records')

        # 6. 各レコードに追加フィールドを設定
        for record in details:
            # 日付変換: YYMMDD → YYYY/MM/DD
            original_date = record['date']  # YYMMDD形式(例: "250115")
            converted_date = convert_date_format(original_date)  # "2025/01/15"
            record['date'] = converted_date

            # 年・月を抽出(変換後のdate "2025/01/15" から)
            date_parts = converted_date.split('/')
            year = int(date_parts[0])
            month = int(date_parts[1])

            record['year'] = year
            record['month'] = month
            record['month_str'] = f"{year}年{month}月"

            # 金額を文字列からintに変換
            record['amount'] = int(record['amount'])

        # 7. プレビュー生成
        preview = generate_preview(details)

        # 8. サマリー情報の計算
        total_count = len(details)
        total_amount = sum(record['amount'] for record in details)

        # 日付範囲の計算(既にYYYY/MM/DD形式に変換済み)
        dates = [record['date'] for record in details]
        date_range = {
            'start': min(dates) if dates else '',
            'end': max(dates) if dates else ''
        }

        # 結果を返す
        return {
            'details': details,
            'preview': preview,
            'total_count': total_count,
            'summary': {
                'total_amount': total_amount,
                'date_range': date_range
            }
        }

    except (PathValidationError, InvalidFileFormatError, EncodingDetectionError,
            DataExtractionError, DateConversionError) as e:
        # 既知のCSV処理エラーはそのまま再発生
        raise

    except Exception as e:
        # 予期しないエラーはCSVProcessingErrorでラップ
        raise CSVProcessingError(
            f"CSV処理中に予期しないエラーが発生しました: {str(e)}",
            details={
                "file_path": file_path,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
