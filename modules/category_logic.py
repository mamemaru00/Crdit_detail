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

使用例:
    # 1. マッピングデータ読み込み
    >>> mapping_data = load_mapping_data('config/mapping.json')

    # 2. 単一店舗のカテゴリ判定
    >>> result = determine_category('ユニクロ池袋店', mapping_data)
    >>> print(result['category'])  # '外食費'
    >>> print(result['column'])    # 'C'

    # 3. 複数レコードの一括判定
    >>> records = [
    ...     {'store': 'ユニクロ池袋', 'amount': 5000},
    ...     {'store': 'AMAZON', 'amount': 3000}
    ... ]
    >>> enriched = determine_categories_batch(records, mapping_data)

    # 4. 未登録店舗の検出
    >>> unregistered = detect_unregistered_stores(records, mapping_data)
    >>> for store in unregistered:
    ...     print(f"{store['store']}: {store['total_amount']}円")
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
PRIORITY_DEFAULT = 999   # デフォルト優先度（マッチしない場合）

# 優先順位の範囲
MIN_PRIORITY = 1
MAX_PRIORITY = 4


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


def _validate_required_fields(entry: dict, required_fields: List[str], context: str = "エントリ") -> None:
    """
    必須フィールドの存在を検証する（内部ヘルパー関数）

    Args:
        entry: 検証対象の辞書
        required_fields: 必須フィールドのリスト
        context: エラーメッセージ用のコンテキスト

    Raises:
        MappingValidationError: 必須フィールドが不足している場合
    """
    missing_fields = [field for field in required_fields if field not in entry]
    if missing_fields:
        raise MappingValidationError(
            f"{context}に必須フィールドが不足しています: {', '.join(missing_fields)}",
            details={'missing_fields': missing_fields, 'entry': entry}
        )


def _validate_field_type(entry: dict, field_name: str, expected_type: type,
                         allow_empty: bool = False) -> None:
    """
    フィールドの型を検証する（内部ヘルパー関数）

    Args:
        entry: 検証対象の辞書
        field_name: フィールド名
        expected_type: 期待される型
        allow_empty: 空文字列を許可するか（文字列型の場合のみ）

    Raises:
        MappingValidationError: 型が一致しない、または空の場合
    """
    value = entry.get(field_name)

    # 型チェック
    if not isinstance(value, expected_type):
        raise MappingValidationError(
            f"{field_name}フィールドは{expected_type.__name__}である必要があります: {value}",
            details={'field': field_name, 'value': value, 'type': type(value).__name__}
        )

    # 文字列の場合、空文字列チェック
    if expected_type == str and not allow_empty and not value:
        raise MappingValidationError(
            f"{field_name}フィールドは空でない文字列である必要があります",
            details={'field': field_name, 'value': value}
        )


def _validate_field_in_choices(entry: dict, field_name: str, valid_choices: List[str],
                                error_hint: str = "") -> None:
    """
    フィールドの値が有効な選択肢に含まれるか検証する（内部ヘルパー関数）

    Args:
        entry: 検証対象の辞書
        field_name: フィールド名
        valid_choices: 有効な選択肢のリスト
        error_hint: エラーメッセージに追加するヒント

    Raises:
        MappingValidationError: 値が有効な選択肢に含まれない場合
    """
    value = entry.get(field_name)
    if value not in valid_choices:
        hint_msg = f"。有効な値: {error_hint}" if error_hint else f"。有効な値: {', '.join(valid_choices)}"
        raise MappingValidationError(
            f"{field_name}が不正です: {value}{hint_msg}",
            details={'field': field_name, 'value': value, 'valid_values': valid_choices}
        )


def validate_mapping_entry(entry: MappingEntry) -> None:
    """
    単一のマッピングエントリを検証する

    Args:
        entry: 検証するマッピングエントリ

    Raises:
        MappingValidationError: 検証エラー時
    """
    # 必須フィールドの存在確認
    required_fields = ['id', 'pattern', 'match_type', 'category', 'column', 'priority']
    _validate_required_fields(entry, required_fields)

    # フィールドの型チェック
    _validate_field_type(entry, 'id', int)
    _validate_field_type(entry, 'pattern', str, allow_empty=False)
    _validate_field_type(entry, 'category', str, allow_empty=False)

    # match_typeの検証
    _validate_field_in_choices(entry, 'match_type', VALID_MATCH_TYPES)

    # columnの検証
    _validate_field_in_choices(entry, 'column', VALID_COLUMNS, error_hint="B～V")

    # priorityの検証（範囲チェック）
    priority = entry.get('priority')
    if not isinstance(priority, int) or priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        raise MappingValidationError(
            f"priorityは{MIN_PRIORITY}～{MAX_PRIORITY}の整数である必要があります: {priority}",
            details={'field': 'priority', 'value': priority}
        )


def _validate_duplicate_ids(mappings: List[MappingEntry]) -> None:
    """
    マッピングエントリのID重複をチェックする（内部ヘルパー関数）

    Args:
        mappings: マッピングエントリのリスト

    Raises:
        MappingValidationError: IDが重複している場合
    """
    id_list = [entry['id'] for entry in mappings if 'id' in entry]
    duplicate_ids = [id_val for id_val in set(id_list) if id_list.count(id_val) > 1]
    if duplicate_ids:
        raise MappingValidationError(
            f"重複するIDが検出されました: {duplicate_ids}",
            details={'duplicate_ids': duplicate_ids}
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
    # versionフィールドの検証
    _validate_required_fields(data, ['version'], context="マッピングデータ")
    _validate_field_type(data, 'version', str)

    # mappingsフィールドの検証
    _validate_required_fields(data, ['mappings'], context="マッピングデータ")
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
    _validate_duplicate_ids(mappings)

    # defaultフィールドの検証
    _validate_required_fields(data, ['default'], context="マッピングデータ")
    if not isinstance(data.get('default'), dict):
        raise InvalidMappingFormatError(
            "defaultフィールドは辞書形式である必要があります",
            details={'type': type(data.get('default')).__name__}
        )

    # defaultフィールドの必須キー確認
    default_data = data.get('default', {})
    _validate_required_fields(default_data, ['category', 'column'], context="defaultフィールド")

    # defaultのcolumnが有効な値か確認
    _validate_field_in_choices(default_data, 'column', VALID_COLUMNS, error_hint="B～V")


def _is_valid_match_input(store_name: str, pattern: str) -> bool:
    """
    マッチング入力の有効性をチェックする（内部ヘルパー関数）

    Args:
        store_name: 店舗名
        pattern: パターン文字列

    Returns:
        bool: 両方が空でない文字列ならTrue
    """
    return bool(store_name and pattern)


def match_exact(store_name: str, pattern: str) -> bool:
    """
    完全一致判定

    Args:
        store_name (str): 店舗名
        pattern (str): パターン文字列

    Returns:
        bool: 一致判定結果

    Example:
        >>> match_exact("ユニクロ", "ユニクロ")
        True
        >>> match_exact("ユニクロ 池袋店", "ユニクロ")
        False
    """
    return _is_valid_match_input(store_name, pattern) and store_name == pattern


def match_startswith(store_name: str, pattern: str) -> bool:
    """
    前方一致判定

    Args:
        store_name (str): 店舗名
        pattern (str): パターン文字列

    Returns:
        bool: 一致判定結果

    Example:
        >>> match_startswith("ユニクロ 池袋店", "ユニクロ")
        True
        >>> match_startswith("池袋ユニクロ", "ユニクロ")
        False
    """
    return _is_valid_match_input(store_name, pattern) and store_name.startswith(pattern)


def match_contains(store_name: str, pattern: str) -> bool:
    """
    部分一致判定

    Args:
        store_name (str): 店舗名
        pattern (str): パターン文字列

    Returns:
        bool: 一致判定結果

    Example:
        >>> match_contains("東京ユニクロ池袋店", "ユニクロ")
        True
        >>> match_contains("無印良品", "ユニクロ")
        False
    """
    return _is_valid_match_input(store_name, pattern) and pattern in store_name


def match_keyword(store_name: str, pattern: str) -> bool:
    """
    キーワード一致判定(スペース区切りでAND条件)

    Args:
        store_name (str): 店舗名
        pattern (str): パターン文字列(スペース区切り)

    Returns:
        bool: 一致判定結果

    Example:
        >>> match_keyword("イオン幕張新都心", "イオン 幕張")
        True
        >>> match_keyword("イオン池袋", "イオン 幕張")
        False
        >>> match_keyword("イオンスタイル幕張新都心", "イオン 幕張")
        True

    Note:
        pattern="イオン 幕張" → "イオン" AND "幕張" が店舗名に含まれる
    """
    if not _is_valid_match_input(store_name, pattern):
        return False

    # スペースで分割してキーワードリストを作成し、すべてが店舗名に含まれるか確認
    return all(keyword in store_name for keyword in pattern.split())


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

    Example:
        >>> entry = {'pattern': 'ユニクロ', 'match_type': 'startswith', ...}
        >>> execute_pattern_match("ユニクロ池袋", entry)
        True
    """
    match_type = entry['match_type']
    pattern = entry['pattern']

    if match_type == MATCH_TYPE_EXACT:
        return match_exact(store_name, pattern)
    elif match_type == MATCH_TYPE_STARTSWITH:
        return match_startswith(store_name, pattern)
    elif match_type == MATCH_TYPE_CONTAINS:
        return match_contains(store_name, pattern)
    elif match_type == MATCH_TYPE_KEYWORD:
        return match_keyword(store_name, pattern)
    else:
        raise CategoryMatchError(
            f"不明なmatch_typeです: {match_type}",
            details={'match_type': match_type, 'pattern': pattern, 'store_name': store_name}
        )


# match_typeの優先順位マップ（定数として定義）
_MATCH_TYPE_PRIORITY_MAP = {
    MATCH_TYPE_EXACT: PRIORITY_EXACT,
    MATCH_TYPE_STARTSWITH: PRIORITY_STARTSWITH,
    MATCH_TYPE_CONTAINS: PRIORITY_CONTAINS,
    MATCH_TYPE_KEYWORD: PRIORITY_KEYWORD
}


def _get_match_priority(entry: MappingEntry) -> tuple[int, int]:
    """
    エントリのマッチ優先度を取得する（内部ヘルパー関数）

    Args:
        entry: マッピングエントリ

    Returns:
        tuple[int, int]: (match_type優先順位, entry priority)
    """
    match_type = entry['match_type']
    type_priority = _MATCH_TYPE_PRIORITY_MAP.get(match_type, PRIORITY_DEFAULT)
    entry_priority = entry.get('priority', PRIORITY_DEFAULT)
    return (type_priority, entry_priority)


def find_best_match(
    store_name: str,
    mappings: List[MappingEntry]
) -> Optional[MappingEntry]:
    """
    優先順位に基づき最適なマッピングを選択

    優先順位:
    1. 完全一致(exact) - PRIORITY_EXACT=1
    2. 前方一致(startswith) - PRIORITY_STARTSWITH=2
    3. 部分一致(contains) - PRIORITY_CONTAINS=3
    4. キーワード一致(keyword) - PRIORITY_KEYWORD=4

    同じmatch_typeの場合は、priorityフィールドで判定（小さい値が優先）

    Args:
        store_name (str): 店舗名
        mappings (List[MappingEntry]): マッピングエントリリスト

    Returns:
        Optional[MappingEntry]: マッチしたエントリ(なければNone)

    Example:
        # "ユニクロ"という店舗名で
        # 1. 完全一致: "ユニクロ" があれば、それを優先
        # 2. 前方一致: "ユニ" があれば、それを次点として選択
    """
    if not store_name or not mappings:
        return None

    # マッチしたエントリのリストを作成
    matched_entries: List[tuple[int, int, MappingEntry]] = []

    for entry in mappings:
        try:
            if execute_pattern_match(store_name, entry):
                # 優先順位を取得して追加
                priority_tuple = _get_match_priority(entry)
                matched_entries.append((*priority_tuple, entry))
        except CategoryMatchError:
            # 不明なmatch_typeの場合はスキップ
            continue

    # マッチしたエントリがない場合
    if not matched_entries:
        return None

    # 優先順位でソート: match_type優先順位 → entry priority
    # min関数を使用してソート処理を効率化
    best_match = min(matched_entries, key=lambda x: (x[0], x[1]))

    # 最も優先度の高いエントリを返す
    return best_match[2]


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

    Example:
        # マッチした場合
        >>> result = determine_category("ユニクロ", mapping_data)
        >>> result['matched']
        True
        >>> result['category']
        '外食費'
        >>> result['column']
        'C'

        # マッチしなかった場合（デフォルト値を使用）
        >>> result = determine_category("未登録店舗", mapping_data)
        >>> result['matched']
        False
        >>> result['category']
        '支払額'
        >>> result['column']
        'B'
    """
    # 1. find_best_matchでマッピング検索
    best_match = find_best_match(store_name, mapping_data['mappings'])

    # 2. マッチした場合
    if best_match:
        return MatchResult(
            matched=True,
            category=best_match['category'],
            column=best_match['column'],
            pattern=best_match['pattern'],
            match_type=best_match['match_type']
        )

    # 3. マッチしなかった場合（デフォルト列）
    default = mapping_data['default']
    return MatchResult(
        matched=False,
        category=default['category'],
        column=default['column'],
        pattern=None,
        match_type=None
    )


def _aggregate_unregistered_store(unregistered_map: Dict[str, Dict[str, int]],
                                  store_name: str, amount: int) -> None:
    """
    未登録店舗を集計マップに追加する（内部ヘルパー関数）

    Args:
        unregistered_map: 未登録店舗の集計マップ
        store_name: 店舗名
        amount: 金額
    """
    if store_name not in unregistered_map:
        unregistered_map[store_name] = {'count': 0, 'total_amount': 0}

    unregistered_map[store_name]['count'] += 1
    unregistered_map[store_name]['total_amount'] += amount


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
        List[Dict]: 未登録店舗リスト（金額降順ソート）
            [
                {
                    'store': '未登録店舗A',
                    'count': 3,  # 出現回数
                    'total_amount': 15000  # 合計金額
                },
                ...
            ]

    Example:
        >>> records = [
        ...     {'store': '未登録A', 'amount': 1000},
        ...     {'store': '未登録A', 'amount': 2000},
        ...     {'store': '未登録B', 'amount': 500}
        ... ]
        >>> result = detect_unregistered_stores(records, mapping_data)
        >>> result[0]['store']
        '未登録A'
        >>> result[0]['total_amount']
        3000
        >>> result[0]['count']
        2
    """
    # 空リストの場合は即座に返却
    if not records:
        return []

    # 未登録店舗を集計するための辞書
    unregistered_map: Dict[str, Dict[str, int]] = {}

    # 各レコードに対してカテゴリ判定を実行
    for record in records:
        # storeフィールドが存在しない場合はスキップ
        store_name = record.get('store')
        if not store_name:
            continue

        # カテゴリ判定を実行
        match_result = determine_category(store_name, mapping_data)

        # matched=Falseの店舗を集計
        if not match_result['matched']:
            amount = record.get('amount', 0)
            _aggregate_unregistered_store(unregistered_map, store_name, amount)

    # 辞書からリスト形式に変換し、金額降順でソート
    return sorted(
        [
            {
                'store': store_name,
                'count': data['count'],
                'total_amount': data['total_amount']
            }
            for store_name, data in unregistered_map.items()
        ],
        key=lambda x: x['total_amount'],
        reverse=True
    )


def _enrich_record_with_category(record: Dict, mapping_data: MappingData) -> Dict:
    """
    レコードにカテゴリ情報を付与する（内部ヘルパー関数）

    Args:
        record: 明細レコード
        mapping_data: マッピングデータ

    Returns:
        Dict: カテゴリ情報付きレコード
    """
    enriched_record = record.copy()

    # storeフィールドが存在する場合のみカテゴリ判定
    store_name = record.get('store')
    if store_name:
        # カテゴリ判定を実行
        match_result = determine_category(store_name, mapping_data)

        # 判定結果をレコードに追加
        enriched_record.update({
            'category': match_result['category'],
            'column': match_result['column'],
            'matched': match_result['matched'],
            'pattern': match_result.get('pattern'),
            'match_type': match_result.get('match_type')
        })
    else:
        # storeフィールドがない場合はデフォルト値を設定
        default = mapping_data['default']
        enriched_record.update({
            'category': default['category'],
            'column': default['column'],
            'matched': False,
            'pattern': None,
            'match_type': None
        })

    return enriched_record


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

    Example:
        >>> records = [
        ...     {'store': 'ユニクロ', 'amount': 1000},
        ...     {'store': '未登録店舗', 'amount': 500}
        ... ]
        >>> results = determine_categories_batch(records, mapping_data)
        >>> results[0]['category']
        '外食費'
        >>> results[0]['matched']
        True
        >>> results[1]['category']
        '支払額'
        >>> results[1]['matched']
        False
    """
    # 空リストの場合は即座に返却
    if not records:
        return []

    # 各レコードにカテゴリ情報を付与
    return [_enrich_record_with_category(record, mapping_data) for record in records]
