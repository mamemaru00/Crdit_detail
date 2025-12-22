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
import platform
import shutil
from datetime import datetime

# OS固有のファイルロックモジュールの条件付きインポート
try:
    if platform.system() == 'Windows':
        import msvcrt
    else:
        import fcntl
except ImportError:
    # インポートエラーは無視（ログで警告）
    pass

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
    logger.info(f"[CRUD:ADD] マッピング追加処理開始 - pattern='{entry.get('pattern')}', "
                f"match_type={entry.get('match_type')}, category='{entry.get('category')}', "
                f"column={entry.get('column')}, priority={entry.get('priority')}")

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
    logger.debug(f"[CRUD:ADD] バリデーション成功: ID={next_id}")

    # 重複チェック（簡易版）
    _check_duplicate(new_entry, mappings)
    logger.debug(f"[CRUD:ADD] 重複チェック成功: ID={next_id}")

    # マッピングリストに追加
    mappings.append(new_entry)
    mapping_data['mappings'] = mappings

    # ファイル保存
    _save_mapping_data(mapping_data)

    logger.info(f"[CRUD:ADD] マッピング追加成功 - ID={next_id}, pattern='{new_entry['pattern']}', "
                f"category='{new_entry['category']}', 総件数={len(mappings)}件")
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
    logger.info(f"[CRUD:UPDATE] マッピング更新処理開始 - ID={mapping_id}, 更新項目={list(entry.keys())}")

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
        logger.warning(f"[CRUD:UPDATE] 更新対象が見つかりません - ID={mapping_id}")
        raise MappingNotFoundError(
            f"ID {mapping_id} のマッピングが見つかりません",
            details={'mapping_id': mapping_id}
        )

    # 更新前の情報をログ出力（監査用）
    logger.debug(f"[CRUD:UPDATE] 更新前 - ID={mapping_id}, pattern='{target_entry.get('pattern')}', "
                 f"category='{target_entry.get('category')}', priority={target_entry.get('priority')}")

    # エントリを更新（部分更新対応）
    updated_entry = target_entry.copy()
    updated_entry.update(entry)
    updated_entry['id'] = mapping_id  # IDは変更不可

    # バリデーション
    validate_mapping_entry(updated_entry)
    logger.debug(f"[CRUD:UPDATE] バリデーション成功: ID={mapping_id}")

    # 重複チェック（自身を除く）
    other_mappings = [m for m in mappings if m.get('id') != mapping_id]
    _check_duplicate(updated_entry, other_mappings)
    logger.debug(f"[CRUD:UPDATE] 重複チェック成功: ID={mapping_id}")

    # リストを更新
    mappings[target_index] = updated_entry
    mapping_data['mappings'] = mappings

    # ファイル保存
    _save_mapping_data(mapping_data)

    logger.info(f"[CRUD:UPDATE] マッピング更新成功 - ID={mapping_id}, pattern='{updated_entry['pattern']}', "
                f"category='{updated_entry['category']}', priority={updated_entry['priority']}")
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
    logger.info(f"[CRUD:DELETE] マッピング削除処理開始 - ID={mapping_id}")

    # 現在のデータを読み込み
    mapping_data = load_mapping_data(DEFAULT_MAPPING_PATH)
    mappings = mapping_data.get('mappings', [])
    original_count = len(mappings)

    # 対象エントリを検索
    target_entry = None
    for entry in mappings:
        if entry.get('id') == mapping_id:
            target_entry = entry
            break

    # 見つからない場合
    if target_entry is None:
        logger.warning(f"[CRUD:DELETE] 削除対象が見つかりません - ID={mapping_id}")
        raise MappingNotFoundError(
            f"ID {mapping_id} のマッピングが見つかりません",
            details={'mapping_id': mapping_id}
        )

    # 削除前の情報をログ出力（監査用）
    logger.debug(f"[CRUD:DELETE] 削除対象 - ID={mapping_id}, pattern='{target_entry.get('pattern')}', "
                 f"category='{target_entry.get('category')}', match_type={target_entry.get('match_type')}")

    # リストから削除
    mappings = [m for m in mappings if m.get('id') != mapping_id]
    mapping_data['mappings'] = mappings

    # ファイル保存
    _save_mapping_data(mapping_data)

    logger.info(f"[CRUD:DELETE] マッピング削除成功 - ID={mapping_id}, pattern='{target_entry.get('pattern')}', "
                f"削除前={original_count}件, 削除後={len(mappings)}件")
    return True


# ==================== プライベート関数（内部処理） ====================

def _create_backup(file_path: Path) -> None:
    """
    マッピングファイルの自動バックアップを作成する（内部ヘルパー関数）

    保存前にタイムスタンプ付きのバックアップファイルを作成し、
    古いバックアップを自動削除して最新10件のみ保持します。

    Args:
        file_path (Path): バックアップ対象のファイルパス

    Note:
        - バックアップは config/backups/ ディレクトリに保存
        - ファイル名形式: mapping_YYYYMMDD_HHMMSS.json
        - 最新10件を保持、それ以外は自動削除
        - バックアップ失敗時は警告ログのみ（処理は続行）
    """
    if not file_path.exists():
        logger.debug(f"バックアップ対象ファイルが存在しません: {file_path}")
        return

    try:
        # バックアップディレクトリ作成
        backup_dir = file_path.parent / 'backups'
        backup_dir.mkdir(exist_ok=True)

        # タイムスタンプ付きバックアップファイル名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"mapping_{timestamp}.json"

        # ファイルコピー（メタデータも保持）
        shutil.copy2(file_path, backup_file)
        logger.info(f"バックアップを作成しました: {backup_file.name}")

        # 古いバックアップ削除（最新10件保持）
        backups = sorted(backup_dir.glob('mapping_*.json'), reverse=True)
        for old_backup in backups[10:]:
            old_backup.unlink()
            logger.info(f"古いバックアップを削除しました: {old_backup.name}")

    except Exception as e:
        # バックアップ失敗は警告のみ（処理は続行）
        logger.warning(f"バックアップ作成に失敗しましたが処理を続行します: {str(e)}")


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
            existing_id = existing.get('id')
            logger.warning(f"[VALIDATION] 重複検出 - pattern='{pattern}', match_type={match_type}, "
                           f"既存ID={existing_id}, 既存category='{existing.get('category')}'")
            raise DuplicateMappingError(
                f"同じpatternとmatch_typeの組み合わせが既に存在します: pattern={pattern}, match_type={match_type}",
                details={
                    'pattern': pattern,
                    'match_type': match_type,
                    'existing_id': existing_id,
                    'existing_category': existing.get('category')
                }
            )


def _save_mapping_data(data: MappingData) -> None:
    """
    マッピングデータをJSONファイルに保存する（内部ヘルパー関数）

    アトミック性を確保するため、一時ファイル経由で保存します。
    Phase 2強化機能:
    - ファイルロック（同時書き込み競合防止）
    - 自動バックアップ作成
    - 詳細なエラーハンドリング

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

    # 保存前にバックアップ作成
    _create_backup(file_path)

    lock_file = None
    try:
        # ファイルロック取得（OS別処理）
        if file_path.exists():
            lock_file = file_path.open('r+', encoding='utf-8')
        else:
            # ファイルが存在しない場合は作成モードで開く
            lock_file = file_path.open('w+', encoding='utf-8')

        # OS別ファイルロック
        if platform.system() == 'Windows':
            try:
                import msvcrt
                # 排他ロック取得（非ブロッキング）
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                logger.debug("ファイルロック取得成功（Windows）")
            except NameError:
                logger.warning("msvcrtモジュールが利用できません。ロックなしで続行します。")
            except OSError as e:
                logger.error(f"ファイルロック取得失敗（Windows）: {str(e)}")
                raise MappingSaveError(
                    f"ファイルロック取得に失敗しました。他のプロセスが使用中の可能性があります: {str(e)}",
                    details={'path': str(file_path), 'error': str(e), 'os': 'Windows'}
                )
        else:
            try:
                import fcntl
                # 排他ロック取得（非ブロッキング）
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.debug("ファイルロック取得成功（Unix/Linux）")
            except NameError:
                logger.warning("fcntlモジュールが利用できません。ロックなしで続行します。")
            except BlockingIOError as e:
                logger.error(f"ファイルロック取得失敗（Unix/Linux）: {str(e)}")
                raise MappingSaveError(
                    f"ファイルロック取得に失敗しました。他のプロセスが使用中の可能性があります: {str(e)}",
                    details={'path': str(file_path), 'error': str(e), 'os': platform.system()}
                )

        # 一時ファイルに書き込み
        try:
            with temp_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"一時ファイルへの書き込み完了: {temp_path}")
        except Exception as e:
            logger.error(f"一時ファイル書き込みエラー: {str(e)}")
            raise MappingSaveError(
                f"一時ファイルへの書き込みに失敗しました: {str(e)}",
                details={'path': str(temp_path), 'error': str(e)}
            )

        # アトミックな置き換え
        try:
            os.replace(temp_path, file_path)
            logger.info(f"マッピングデータを保存しました: {file_path} ({len(data.get('mappings', []))}件)")
        except Exception as e:
            logger.error(f"ファイル置き換えエラー: {str(e)}")
            raise MappingSaveError(
                f"ファイルの置き換えに失敗しました: {str(e)}",
                details={'path': str(file_path), 'temp_path': str(temp_path), 'error': str(e)}
            )

    except MappingSaveError:
        # 既に適切な例外が発生している場合は再スロー
        raise

    except Exception as e:
        # 予期しないエラー
        logger.error(f"マッピング保存中に予期しないエラーが発生しました: {str(e)}")
        raise MappingSaveError(
            f"マッピングファイルの保存に失敗しました: {str(e)}",
            details={'path': str(file_path), 'error': str(e)}
        )

    finally:
        # ファイルロック解放
        if lock_file is not None:
            try:
                # ファイルを閉じることでロックも解放される
                lock_file.close()
                logger.debug("ファイルロック解放完了")
            except Exception as e:
                logger.warning(f"ファイルロック解放中にエラーが発生しました: {str(e)}")

        # エラー時は一時ファイルを削除
        if temp_path.exists():
            try:
                temp_path.unlink()
                logger.debug(f"一時ファイルを削除しました: {temp_path}")
            except Exception as e:
                logger.warning(f"一時ファイル削除中にエラーが発生しました: {str(e)}")
