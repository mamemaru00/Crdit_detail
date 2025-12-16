"""
マッピング管理モジュール

このモジュールはconfig/mapping.jsonのCRUD操作を提供します。

主な機能:
- マッピングデータのCRUD操作（追加、読込、更新、削除）
- マッピングデータのバリデーション
- JSONファイルの読み書き・永続化
- ID自動採番管理
- データ整合性の保証（重複チェック、アトミック保存）

使用例:
    # 1. 全マッピング取得
    >>> mappings = get_all_mappings()

    # 2. ID検索
    >>> mapping = get_mapping_by_id(1)

    # 3. 新規追加
    >>> new_entry = {
    ...     'pattern': 'ユニクロ',
    ...     'match_type': 'contains',
    ...     'category': '衣服費',
    ...     'column': 'E',
    ...     'priority': 1
    ... }
    >>> added = add_mapping(new_entry)

    # 4. 更新
    >>> updated = update_mapping(1, {'priority': 2})

    # 5. 削除
    >>> deleted = delete_mapping(1)
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict
import logging

# category_logic.pyから型定義と検証関数をインポート
from modules.category_logic import (
    MappingEntry,
    MappingData,
    load_mapping_data,
    validate_mapping_entry,
    validate_mapping_data,
    VALID_MATCH_TYPES,
    VALID_COLUMNS,
    DEFAULT_MAPPING_PATH
)


# ==================== ロガー設定 ====================

logger = logging.getLogger(__name__)


# ==================== カスタム例外クラス ====================

class MappingManagerError(Exception):
    """マッピング管理の基底例外クラス

    すべてのマッピング管理関連例外の基底クラスです。
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


class MappingNotFoundError(MappingManagerError):
    """マッピングが見つからないエラー

    指定されたIDのマッピングエントリが存在しない場合に発生します。
    """
    pass


class DuplicateMappingError(MappingManagerError):
    """マッピング重複エラー

    同一のpatternとmatch_typeの組み合わせが既に存在する場合に発生します。
    """
    pass


class MappingSaveError(MappingManagerError):
    """マッピング保存エラー

    マッピングファイルへの保存処理が失敗した場合に発生します。
    """
    pass


# ==================== パブリック関数（CRUD操作） ====================

def get_all_mappings() -> List[MappingEntry]:
    """
    全マッピングエントリを取得する

    Returns:
        List[MappingEntry]: マッピングエントリのリスト

    Raises:
        MappingLoadError: ファイル読み込みエラー時

    Example:
        >>> mappings = get_all_mappings()
        >>> len(mappings)
        10
    """
    logger.info("マッピング一覧を取得中")
    mapping_data = load_mapping_data(DEFAULT_MAPPING_PATH)
    mappings = mapping_data.get('mappings', [])
    logger.info(f"マッピング一覧を取得しました: {len(mappings)}件")
    return mappings


def get_mapping_by_id(mapping_id: int) -> Optional[MappingEntry]:
    """
    ID指定でマッピングエントリを取得する

    Args:
        mapping_id (int): マッピングID

    Returns:
        Optional[MappingEntry]: マッピングエントリ。見つからない場合はNone

    Example:
        >>> mapping = get_mapping_by_id(1)
        >>> mapping['pattern']
        'ユシンヤ'
    """
    logger.info(f"マッピングID {mapping_id} を検索中")
    mappings = get_all_mappings()

    for entry in mappings:
        if entry.get('id') == mapping_id:
            logger.info(f"マッピングID {mapping_id} が見つかりました")
            return entry

    logger.warning(f"マッピングID {mapping_id} が見つかりませんでした")
    return None


def get_next_id() -> int:
    """
    次のマッピングIDを生成する

    Returns:
        int: 次のID（最大ID + 1）。エントリがない場合は1

    Example:
        >>> get_next_id()
        3
    """
    logger.info("次のIDを生成中")
    mappings = get_all_mappings()

    if not mappings:
        logger.info("マッピングが空のため、ID 1 を返却")
        return 1

    max_id = max(entry.get('id', 0) for entry in mappings)
    next_id = max_id + 1
    logger.info(f"次のID: {next_id} を生成しました")
    return next_id


def add_mapping(entry: Dict) -> MappingEntry:
    """
    新規マッピングエントリを追加する

    Args:
        entry (Dict): 追加するマッピングエントリ（IDは自動採番）
            必須フィールド:
                - pattern (str): 店舗名パターン
                - match_type (str): 一致方法(exact, startswith, contains, keyword)
                - category (str): カテゴリ名
                - column (str): 列番号(B～V)
                - priority (int): 優先順位(1～4)
            オプショナルフィールド:
                - note (str): 備考

    Returns:
        MappingEntry: 追加されたマッピングエントリ（IDを含む）

    Raises:
        MappingValidationError: バリデーションエラー時
        DuplicateMappingError: 重複エラー時
        MappingSaveError: 保存エラー時

    Example:
        >>> new_entry = {
        ...     'pattern': 'ユニクロ',
        ...     'match_type': 'contains',
        ...     'category': '衣服費',
        ...     'column': 'E',
        ...     'priority': 1
        ... }
        >>> added = add_mapping(new_entry)
        >>> added['id']
        3
    """
    logger.info(f"マッピング追加処理開始: pattern={entry.get('pattern')}, category={entry.get('category')}")

    # 現在のデータを読み込み
    mapping_data = load_mapping_data(DEFAULT_MAPPING_PATH)
    mappings = mapping_data.get('mappings', [])

    # 次のIDを生成
    next_id = get_next_id()

    # エントリにIDを付与
    new_entry = entry.copy()
    new_entry['id'] = next_id

    # バリデーション
    validate_mapping_entry(new_entry)

    # 重複チェック（簡易版）
    _check_duplicate(new_entry, mappings)

    # マッピングリストに追加
    mappings.append(new_entry)
    mapping_data['mappings'] = mappings

    # ファイル保存
    _save_mapping_data(mapping_data)

    logger.info(f"マッピング追加完了: ID={next_id}, pattern={new_entry['pattern']}")
    return new_entry


def update_mapping(mapping_id: int, entry: Dict) -> MappingEntry:
    """
    マッピングエントリを更新する

    Args:
        mapping_id (int): 更新対象のマッピングID
        entry (Dict): 更新内容（部分更新対応）

    Returns:
        MappingEntry: 更新後のマッピングエントリ

    Raises:
        MappingNotFoundError: 指定IDが見つからない場合
        MappingValidationError: バリデーションエラー時
        DuplicateMappingError: 重複エラー時
        MappingSaveError: 保存エラー時

    Example:
        >>> updated = update_mapping(1, {'priority': 2})
        >>> updated['priority']
        2
    """
    logger.info(f"マッピング更新処理開始: ID={mapping_id}")

    # 現在のデータを読み込み
    mapping_data = load_mapping_data(DEFAULT_MAPPING_PATH)
    mappings = mapping_data.get('mappings', [])

    # 対象エントリを検索
    target_entry = None
    target_index = -1

    for index, existing_entry in enumerate(mappings):
        if existing_entry.get('id') == mapping_id:
            target_entry = existing_entry
            target_index = index
            break

    # 見つからない場合
    if target_entry is None:
        raise MappingNotFoundError(
            f"ID {mapping_id} のマッピングが見つかりません",
            details={'mapping_id': mapping_id}
        )

    # エントリを更新（部分更新対応）
    updated_entry = target_entry.copy()
    updated_entry.update(entry)
    updated_entry['id'] = mapping_id  # IDは変更不可

    # バリデーション
    validate_mapping_entry(updated_entry)

    # 重複チェック（自身を除く）
    other_mappings = [m for m in mappings if m.get('id') != mapping_id]
    _check_duplicate(updated_entry, other_mappings)

    # リストを更新
    mappings[target_index] = updated_entry
    mapping_data['mappings'] = mappings

    # ファイル保存
    _save_mapping_data(mapping_data)

    logger.info(f"マッピング更新完了: ID={mapping_id}")
    return updated_entry


def delete_mapping(mapping_id: int) -> bool:
    """
    マッピングエントリを削除する

    Args:
        mapping_id (int): 削除対象のマッピングID

    Returns:
        bool: 削除成功時True

    Raises:
        MappingNotFoundError: 指定IDが見つからない場合
        MappingSaveError: 保存エラー時

    Example:
        >>> result = delete_mapping(1)
        >>> result
        True
    """
    logger.info(f"マッピング削除処理開始: ID={mapping_id}")

    # 現在のデータを読み込み
    mapping_data = load_mapping_data(DEFAULT_MAPPING_PATH)
    mappings = mapping_data.get('mappings', [])

    # 対象エントリを検索
    target_entry = None
    for entry in mappings:
        if entry.get('id') == mapping_id:
            target_entry = entry
            break

    # 見つからない場合
    if target_entry is None:
        raise MappingNotFoundError(
            f"ID {mapping_id} のマッピングが見つかりません",
            details={'mapping_id': mapping_id}
        )

    # リストから削除
    mappings = [m for m in mappings if m.get('id') != mapping_id]
    mapping_data['mappings'] = mappings

    # ファイル保存
    _save_mapping_data(mapping_data)

    logger.info(f"マッピング削除完了: ID={mapping_id}, pattern={target_entry.get('pattern')}")
    return True


# ==================== プライベート関数（内部処理） ====================

def _check_duplicate(entry: MappingEntry, existing_mappings: List[MappingEntry]) -> None:
    """
    マッピングエントリの重複をチェックする（内部ヘルパー関数）

    重複判定基準: patternとmatch_typeの組み合わせが同一

    Args:
        entry: チェック対象のエントリ
        existing_mappings: 既存のマッピングリスト

    Raises:
        DuplicateMappingError: 重複が検出された場合
    """
    pattern = entry.get('pattern')
    match_type = entry.get('match_type')

    for existing in existing_mappings:
        if (existing.get('pattern') == pattern and
                existing.get('match_type') == match_type):
            raise DuplicateMappingError(
                f"同じpatternとmatch_typeの組み合わせが既に存在します: pattern={pattern}, match_type={match_type}",
                details={
                    'pattern': pattern,
                    'match_type': match_type,
                    'existing_id': existing.get('id')
                }
            )


def _save_mapping_data(data: MappingData) -> None:
    """
    マッピングデータをJSONファイルに保存する（内部ヘルパー関数）

    アトミック性を確保するため、一時ファイル経由で保存します。

    Args:
        data (MappingData): 保存するマッピングデータ

    Raises:
        MappingValidationError: データ検証エラー時
        MappingSaveError: 保存エラー時
    """
    # データ全体のバリデーション
    validate_mapping_data(data)

    file_path = Path(DEFAULT_MAPPING_PATH)
    temp_path = file_path.with_suffix('.json.tmp')

    try:
        # 一時ファイルに書き込み
        with temp_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # アトミックな置き換え
        os.replace(temp_path, file_path)

        logger.info(f"マッピングデータを保存しました: {file_path}")

    except Exception as e:
        # エラー時は一時ファイルを削除
        if temp_path.exists():
            temp_path.unlink()

        logger.error(f"マッピング保存エラー: {str(e)}")
        raise MappingSaveError(
            f"マッピングファイルの保存に失敗しました: {str(e)}",
            details={'path': str(file_path), 'error': str(e)}
        )
