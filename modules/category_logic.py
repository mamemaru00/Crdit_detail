"""
イオンカード明細カテゴリ判定エンジン

このモジュールは店舗名からカテゴリを自動判定し、
Googleスプレッドシートの該当列へマッピングする機能を提供します。

主な機能:
- マッピングデータ読み込み(config/mapping.json)
- パターンマッチング(完全一致、前方一致、部分一致、キーワード一致)
- 優先順位に基づくカテゴリ決定
- 未登録店舗の検出と集計
- バッチ処理によるカテゴリ一括判定
"""

import json
from pathlib import Path
from typing import TypedDict, List, Optional, Dict


# ==================== 定数定義 ====================

# ファイルパス
DEFAULT_MAPPING_PATH = 'config/mapping.json'

# マッチタイプ
MATCH_TYPE_EXACT = 'exact'        # 完全一致
MATCH_TYPE_STARTSWITH = 'startswith'  # 前方一致
MATCH_TYPE_CONTAINS = 'contains'    # 部分一致
MATCH_TYPE_KEYWORD = 'keyword'      # キーワード一致

VALID_MATCH_TYPES = [
    MATCH_TYPE_EXACT,
    MATCH_TYPE_STARTSWITH,
    MATCH_TYPE_CONTAINS,
    MATCH_TYPE_KEYWORD
]

# デフォルト列
DEFAULT_COLUMN = 'B'
DEFAULT_CATEGORY = '支払額'

# 列範囲(B～V列、21要素)
VALID_COLUMNS = [
    'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
    'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
    'T', 'U', 'V'
]

# 優先順位定数
PRIORITY_EXACT = 1       # 完全一致の優先度
PRIORITY_STARTSWITH = 2  # 前方一致の優先度
PRIORITY_CONTAINS = 3    # 部分一致の優先度
PRIORITY_KEYWORD = 4     # キーワード一致の優先度


# ==================== 型定義（TypedDict） ====================

class MappingEntry(TypedDict):
    """マッピングエントリの型定義

    Attributes:
        id (int): マッピングID
        pattern (str): 店舗名パターン
        match_type (str): 一致方法(exact, startswith, contains, keyword)
        category (str): カテゴリ名
        column (str): 列番号(B～V)
        priority (int): 優先順位(1=最高)
        note (Optional[str]): 備考
    """
    id: int
    pattern: str
    match_type: str
    category: str
    column: str
    priority: int
    note: Optional[str]


class MappingData(TypedDict):
    """マッピングデータ全体の型定義

    Attributes:
        version (str): データバージョン
        mappings (List[MappingEntry]): マッピングエントリリスト
        default (dict): デフォルト設定(category, column)
    """
    version: str
    mappings: List[MappingEntry]
    default: dict


class MatchResult(TypedDict):
    """マッチング結果の型定義

    Attributes:
        matched (bool): マッチしたかどうか
        category (str): カテゴリ名
        column (str): 列番号(B～V)
        pattern (Optional[str]): マッチしたパターン
        match_type (Optional[str]): マッチタイプ
    """
    matched: bool
    category: str
    column: str
    pattern: Optional[str]
    match_type: Optional[str]


# ==================== カスタム例外クラス ====================

class CategoryLogicError(Exception):
    """カテゴリ判定の基底例外クラス

    すべてのカテゴリ判定関連例外の基底クラスです。
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


class MappingLoadError(CategoryLogicError):
    """マッピングデータ読み込みエラー

    マッピングファイルが存在しない、読み込めない場合に発生します。
    ファイルパスのアクセス権限エラーや物理的な存在確認失敗時に使用されます。
    """
    pass


class MappingValidationError(CategoryLogicError):
    """マッピングデータ検証エラー

    マッピングデータの構造や値が期待される形式と異なる場合に発生します。
    必須フィールドの不足、不正な値、ID重複などの検証失敗時に使用されます。
    """
    pass


class CategoryMatchError(CategoryLogicError):
    """カテゴリマッチングエラー

    カテゴリマッチング処理中にエラーが発生した場合に使用します。
    不明なmatch_typeの指定やパターンマッチング実行時のエラーを表します。
    """
    pass


class InvalidMappingFormatError(CategoryLogicError):
    """無効なマッピング形式エラー

    マッピングファイルのJSON形式が不正な場合に発生します。
    JSON解析エラーやデータ型の不一致時に使用されます。
    """
    pass


# ==================== Phase 2以降の関数スケルトン ====================
# Phase 2, 3, 4で実装予定の関数を定義(pass実装)

def load_mapping_data(mapping_path: str = DEFAULT_MAPPING_PATH) -> MappingData:
    """
    マッピングデータをJSONファイルから読み込む

    Args:
        mapping_path: マッピングファイルのパス（デフォルト: config/mapping.json）

    Returns:
        MappingData: 読み込んだマッピングデータ

    Raises:
        MappingLoadError: ファイルが存在しない、または読み込みエラー
        InvalidMappingFormatError: JSON形式が不正
        MappingValidationError: 必須フィールドが不足
    """
    # ファイルパスをPathオブジェクトに変換
    file_path = Path(mapping_path)

    # ファイル存在確認
    if not file_path.exists():
        raise MappingLoadError(
            f"マッピングファイルが見つかりません: {mapping_path}",
            details={'path': str(file_path)}
        )

    if not file_path.is_file():
        raise MappingLoadError(
            f"指定されたパスはファイルではありません: {mapping_path}",
            details={'path': str(file_path)}
        )

    # JSONファイル読み込み
    try:
        with file_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise InvalidMappingFormatError(
            f"JSONファイルの解析に失敗しました: {e.msg}",
            details={'path': str(file_path), 'error': str(e)}
        )
    except PermissionError:
        raise MappingLoadError(
            f"ファイルの読み込み権限がありません: {mapping_path}",
            details={'path': str(file_path)}
        )
    except Exception as e:
        raise MappingLoadError(
            f"ファイルの読み込み中にエラーが発生しました: {str(e)}",
            details={'path': str(file_path), 'error': str(e)}
        )

    # 必須フィールドの検証
    required_fields = ['version', 'mappings', 'default']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise MappingValidationError(
            f"必須フィールドが不足しています: {', '.join(missing_fields)}",
            details={'missing_fields': missing_fields, 'path': str(file_path)}
        )

    # mappingsがリストであることを確認
    if not isinstance(data.get('mappings'), list):
        raise InvalidMappingFormatError(
            "mappingsフィールドはリスト形式である必要があります",
            details={'type': type(data.get('mappings')).__name__, 'path': str(file_path)}
        )

    # defaultが辞書であることを確認
    if not isinstance(data.get('default'), dict):
        raise InvalidMappingFormatError(
            "defaultフィールドは辞書形式である必要があります",
            details={'type': type(data.get('default')).__name__, 'path': str(file_path)}
        )

    return data


def validate_mapping_entry(entry: MappingEntry) -> None:
    """
    単一のマッピングエントリを検証する

    Args:
        entry: 検証するマッピングエントリ

    Raises:
        MappingValidationError: 検証エラー時
    """
    # 必須フィールドのリスト
    required_fields = ['id', 'pattern', 'match_type', 'category', 'column', 'priority']

    # 必須フィールドの存在確認
    missing_fields = [field for field in required_fields if field not in entry]
    if missing_fields:
        raise MappingValidationError(
            f"エントリに必須フィールドが不足しています: {', '.join(missing_fields)}",
            details={'missing_fields': missing_fields, 'entry': entry}
        )

    # フィールドの型チェック
    if not isinstance(entry.get('id'), int):
        raise MappingValidationError(
            f"idフィールドは整数である必要があります: {entry.get('id')}",
            details={'field': 'id', 'value': entry.get('id'), 'type': type(entry.get('id')).__name__}
        )

    if not isinstance(entry.get('pattern'), str) or not entry.get('pattern'):
        raise MappingValidationError(
            f"patternフィールドは空でない文字列である必要があります",
            details={'field': 'pattern', 'value': entry.get('pattern')}
        )

    if not isinstance(entry.get('category'), str) or not entry.get('category'):
        raise MappingValidationError(
            f"categoryフィールドは空でない文字列である必要があります",
            details={'field': 'category', 'value': entry.get('category')}
        )

    # match_typeの検証
    match_type = entry.get('match_type')
    if match_type not in VALID_MATCH_TYPES:
        raise MappingValidationError(
            f"match_typeが不正です: {match_type}。有効な値: {', '.join(VALID_MATCH_TYPES)}",
            details={'field': 'match_type', 'value': match_type, 'valid_values': VALID_MATCH_TYPES}
        )

    # columnの検証
    column = entry.get('column')
    if column not in VALID_COLUMNS:
        raise MappingValidationError(
            f"columnが不正です: {column}。有効な値: B～V",
            details={'field': 'column', 'value': column, 'valid_values': VALID_COLUMNS}
        )

    # priorityの検証
    priority = entry.get('priority')
    if not isinstance(priority, int) or priority < 1 or priority > 4:
        raise MappingValidationError(
            f"priorityは1～4の整数である必要があります: {priority}",
            details={'field': 'priority', 'value': priority}
        )


def validate_mapping_data(data: MappingData) -> None:
    """
    マッピングデータ全体を検証する

    Args:
        data: 検証するマッピングデータ

    Raises:
        MappingValidationError: データ検証エラー時
        InvalidMappingFormatError: 形式エラー時
    """
    # versionフィールドの存在確認
    if 'version' not in data:
        raise MappingValidationError(
            "versionフィールドが存在しません",
            details={'data': data}
        )

    if not isinstance(data.get('version'), str):
        raise InvalidMappingFormatError(
            "versionフィールドは文字列である必要があります",
            details={'type': type(data.get('version')).__name__}
        )

    # mappingsフィールドの検証
    if 'mappings' not in data:
        raise MappingValidationError(
            "mappingsフィールドが存在しません",
            details={'data': data}
        )

    if not isinstance(data.get('mappings'), list):
        raise InvalidMappingFormatError(
            "mappingsフィールドはリスト形式である必要があります",
            details={'type': type(data.get('mappings')).__name__}
        )

    # 各マッピングエントリを検証
    mappings = data.get('mappings', [])
    for index, entry in enumerate(mappings):
        try:
            validate_mapping_entry(entry)
        except MappingValidationError as e:
            # エントリのインデックス情報を追加
            raise MappingValidationError(
                f"mappings[{index}]の検証エラー: {e.message}",
                details={'index': index, 'entry': entry, 'original_error': e.details}
            )

    # ID重複チェック
    id_list = [entry.get('id') for entry in mappings if 'id' in entry]
    duplicate_ids = [id_val for id_val in set(id_list) if id_list.count(id_val) > 1]
    if duplicate_ids:
        raise MappingValidationError(
            f"重複するIDが検出されました: {duplicate_ids}",
            details={'duplicate_ids': duplicate_ids}
        )

    # defaultフィールドの検証
    if 'default' not in data:
        raise MappingValidationError(
            "defaultフィールドが存在しません",
            details={'data': data}
        )

    if not isinstance(data.get('default'), dict):
        raise InvalidMappingFormatError(
            "defaultフィールドは辞書形式である必要があります",
            details={'type': type(data.get('default')).__name__}
        )

    # defaultフィールドの必須キー確認
    default_data = data.get('default', {})
    required_default_keys = ['category', 'column']
    missing_default_keys = [key for key in required_default_keys if key not in default_data]

    if missing_default_keys:
        raise MappingValidationError(
            f"defaultフィールドに必須キーが不足しています: {', '.join(missing_default_keys)}",
            details={'missing_keys': missing_default_keys, 'default': default_data}
        )

    # defaultのcolumnが有効な値か確認
    default_column = default_data.get('column')
    if default_column not in VALID_COLUMNS:
        raise MappingValidationError(
            f"defaultのcolumnが不正です: {default_column}。有効な値: B～V",
            details={'field': 'default.column', 'value': default_column, 'valid_values': VALID_COLUMNS}
        )


def match_exact(store_name: str, pattern: str) -> bool:
    """
    完全一致判定

    Args:
        store_name (str): 店舗名
        pattern (str): パターン文字列

    Returns:
        bool: 一致判定結果
    """
    pass


def match_startswith(store_name: str, pattern: str) -> bool:
    """
    前方一致判定

    Args:
        store_name (str): 店舗名
        pattern (str): パターン文字列

    Returns:
        bool: 一致判定結果
    """
    pass


def match_contains(store_name: str, pattern: str) -> bool:
    """
    部分一致判定

    Args:
        store_name (str): 店舗名
        pattern (str): パターン文字列

    Returns:
        bool: 一致判定結果
    """
    pass


def match_keyword(store_name: str, pattern: str) -> bool:
    """
    キーワード一致判定(スペース区切りでAND条件)

    Args:
        store_name (str): 店舗名
        pattern (str): パターン文字列(スペース区切り)

    Returns:
        bool: 一致判定結果

    Example:
        pattern="イオン 幕張" → "イオン" AND "幕張" が店舗名に含まれる
    """
    pass


def execute_pattern_match(store_name: str, entry: MappingEntry) -> bool:
    """
    マッピングエントリに基づいてパターンマッチングを実行

    Args:
        store_name (str): 店舗名
        entry (MappingEntry): マッピングエントリ

    Returns:
        bool: マッチ結果

    Raises:
        CategoryMatchError: 不明なmatch_type
    """
    pass


def find_best_match(
    store_name: str,
    mappings: List[MappingEntry]
) -> Optional[MappingEntry]:
    """
    優先順位に基づき最適なマッピングを選択

    優先順位:
    1. 完全一致(exact)
    2. 前方一致(startswith)
    3. 部分一致(contains)
    4. キーワード一致(keyword)

    同じmatch_typeの場合は、priorityフィールドで判定

    Args:
        store_name (str): 店舗名
        mappings (List[MappingEntry]): マッピングエントリリスト

    Returns:
        Optional[MappingEntry]: マッチしたエントリ(なければNone)
    """
    pass


def determine_category(
    store_name: str,
    mapping_data: MappingData
) -> MatchResult:
    """
    店舗名からカテゴリと列番号を決定

    Args:
        store_name (str): 店舗名
        mapping_data (MappingData): マッピングデータ

    Returns:
        MatchResult: マッチング結果
            {
                'matched': bool,  # マッチしたかどうか
                'category': str,  # カテゴリ名
                'column': str,    # 列番号(B～V)
                'pattern': Optional[str],  # マッチしたパターン
                'match_type': Optional[str]  # マッチタイプ
            }
    """
    pass


def detect_unregistered_stores(
    records: List[Dict],
    mapping_data: MappingData
) -> List[Dict]:
    """
    未登録店舗を検出し、店舗ごとの金額合計を算出

    Args:
        records (List[Dict]): 明細レコードリスト(csv_processor.pyの出力)
            例: [
                {'date': '2025/08/15', 'store': 'ユシンヤ', 'amount': 5780, ...},
                {'date': '2025/08/16', 'store': 'AMAZON', 'amount': 1200, ...}
            ]
        mapping_data (MappingData): マッピングデータ

    Returns:
        List[Dict]: 未登録店舗リスト
            [
                {
                    'store': '未登録店舗A',
                    'count': 3,  # 出現回数
                    'total_amount': 15000  # 合計金額
                },
                ...
            ]
    """
    pass


def determine_categories_batch(
    records: List[Dict],
    mapping_data: MappingData
) -> List[Dict]:
    """
    複数レコードのカテゴリを一括決定

    Args:
        records (List[Dict]): 明細レコードリスト
        mapping_data (MappingData): マッピングデータ

    Returns:
        List[Dict]: カテゴリ情報付きレコードリスト
            [
                {
                    'date': '2025/08/15',
                    'store': 'ユシンヤ',
                    'amount': 5780,
                    'category': '外食費',
                    'column': 'C',
                    'matched': True
                },
                ...
            ]
    """
    pass
