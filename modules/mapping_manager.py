"""
マッピング管理モジュール

このモジュールはdata/mapping.jsonのCRUD操作を提供します。

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
import sqlite3

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


# ==================== データベース設定 ====================

DEFAULT_DB_PATH = 'data/mappings.db'


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


# ==================== SQLiteデータベース初期化 ====================

def init_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    SQLiteデータベースを初期化する

    データベースファイルが存在しない場合は新規作成し、
    store_mappingsテーブル、インデックス、トリガーを作成します。
    既に存在する場合は何もしません。

    Args:
        db_path (str): データベースファイルのパス

    Raises:
        MappingSaveError: データベース初期化エラー時

    Example:
        >>> init_database('data/mappings.db')
    """
    logger.info(f"データベース初期化処理を開始: {db_path}")

    try:
        # データディレクトリが存在しない場合は作成
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # WALモード有効化（同時実行性向上）
        cursor.execute("PRAGMA journal_mode=WAL")
        logger.debug("WALモードを有効化しました")

        # テーブル作成（既に存在する場合はスキップ）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL UNIQUE,
                match_type TEXT NOT NULL CHECK(match_type IN ('exact', 'startswith', 'contains', 'keyword')),
                category TEXT NOT NULL,
                column_name TEXT NOT NULL CHECK(LENGTH(column_name) = 1 AND column_name >= 'C' AND column_name <= 'V'),
                priority INTEGER NOT NULL CHECK(priority >= 1 AND priority <= 4),
                source TEXT NOT NULL DEFAULT 'manual' CHECK(source IN ('manual', 'auto')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.debug("store_mappingsテーブルを作成しました")

        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern ON store_mappings(pattern)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_type ON store_mappings(match_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON store_mappings(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON store_mappings(source)")
        logger.debug("インデックスを作成しました")

        # 更新トリガー作成
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_timestamp
            AFTER UPDATE ON store_mappings
            FOR EACH ROW
            BEGIN
                UPDATE store_mappings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        logger.debug("更新トリガーを作成しました")

        conn.commit()
        conn.close()

        logger.info(f"データベース初期化が完了しました: {db_path}")

    except sqlite3.Error as e:
        logger.error(f"データベース初期化エラー: {str(e)}")
        raise MappingSaveError(
            f"データベースの初期化に失敗しました: {str(e)}",
            details={'db_path': db_path, 'error': str(e)}
        )
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {str(e)}")
        raise MappingSaveError(
            f"データベース初期化中に予期しないエラーが発生しました: {str(e)}",
            details={'db_path': db_path, 'error': str(e)}
        )


def _get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    データベース接続を取得する（内部ヘルパー関数）

    Args:
        db_path (str): データベースファイルのパス

    Returns:
        sqlite3.Connection: データベース接続オブジェクト

    Note:
        - Row factoryを設定して辞書形式でデータを取得可能にする
        - WALモードを有効化
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 辞書形式でデータ取得
    conn.execute("PRAGMA journal_mode=WAL")  # WALモード有効化
    return conn


def ensure_database_initialized(db_path: str = DEFAULT_DB_PATH, json_path: str = DEFAULT_MAPPING_PATH) -> None:
    """
    データベースが初期化されていることを保証する

    データベースファイルが存在しない場合:
    1. データベースを初期化
    2. JSONファイルが存在すれば自動移行

    Args:
        db_path (str): データベースファイルのパス
        json_path (str): JSONファイルのパス

    Note:
        この関数はモジュールインポート時に自動的に呼び出されます
    """
    db_file = Path(db_path)
    json_file = Path(json_path)

    # データベースが既に存在する場合は何もしない
    if db_file.exists():
        return

    logger.info("データベースファイルが存在しないため、初期化を実行します")

    try:
        # データベース初期化
        init_database(db_path)

        # JSONファイルが存在する場合は自動移行
        if json_file.exists():
            logger.info("JSONファイルが見つかりました。自動移行を実行します")
            # 簡易的な移行処理（migrate_json_to_sqlite.pyを使わない）
            json_data = load_mapping_data(json_path)
            mappings = json_data.get('mappings', [])

            if mappings:
                conn = _get_db_connection(db_path)
                cursor = conn.cursor()
                conn.execute("BEGIN TRANSACTION")

                migrated_count = 0
                for entry in mappings:
                    pattern = entry.get('pattern')
                    match_type = entry.get('match_type')
                    category = entry.get('category')
                    column = entry.get('column')
                    priority = entry.get('priority', 1)

                    if not all([pattern, match_type, category, column]):
                        continue

                    try:
                        cursor.execute("""
                            INSERT INTO store_mappings (pattern, match_type, category, column_name, priority, source)
                            VALUES (?, ?, ?, ?, ?, 'manual')
                        """, (pattern, match_type, category, column, priority))
                        migrated_count += 1
                    except sqlite3.IntegrityError:
                        # 重複はスキップ
                        continue

                conn.commit()
                conn.close()

                logger.info(f"JSONからの自動移行が完了しました: {migrated_count}件")

    except Exception as e:
        logger.warning(f"データベース自動初期化に失敗しました: {str(e)}")
        logger.warning("JSONモードで動作します")


# ==================== パブリック関数（CRUD操作） ====================

def get_all_mappings(use_sqlite: bool = True) -> List[MappingEntry]:
    """
    全マッピングエントリを取得する

    Args:
        use_sqlite (bool): SQLiteを使用するか（デフォルト: True）

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

    # SQLiteモード
    if use_sqlite and Path(DEFAULT_DB_PATH).exists():
        try:
            conn = _get_db_connection(DEFAULT_DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, pattern, match_type, category, column_name as column, priority, source
                FROM store_mappings
                ORDER BY priority ASC, id ASC
            """)

            mappings = []
            for row in cursor.fetchall():
                mappings.append({
                    'id': row['id'],
                    'pattern': row['pattern'],
                    'match_type': row['match_type'],
                    'category': row['category'],
                    'column': row['column'],  # column_name -> column に変換
                    'priority': row['priority']
                })

            conn.close()
            logger.info(f"マッピング一覧を取得しました（SQLite）: {len(mappings)}件")
            return mappings

        except Exception as e:
            logger.error(f"SQLiteからのマッピング取得に失敗: {str(e)}")
            # フォールバックしてJSONから読み込み
            logger.warning("JSONファイルから読み込みます")

    # JSONモード（フォールバック）
    if Path(DEFAULT_MAPPING_PATH).exists():
        mapping_data = load_mapping_data(DEFAULT_MAPPING_PATH)
        mappings = mapping_data.get('mappings', [])
        logger.info(f"マッピング一覧を取得しました（JSON）: {len(mappings)}件")
        return mappings
    else:
        logger.warning("マッピングデータが見つかりません")
        return []


def get_mapping_by_id(mapping_id: int, use_sqlite: bool = True) -> Optional[MappingEntry]:
    """
    ID指定でマッピングエントリを取得する

    Args:
        mapping_id (int): マッピングID
        use_sqlite (bool): SQLiteを使用するか（デフォルト: True）

    Returns:
        Optional[MappingEntry]: マッピングエントリ。見つからない場合はNone

    Example:
        >>> mapping = get_mapping_by_id(1)
        >>> mapping['pattern']
        'ユシンヤ'
    """
    logger.info(f"マッピングID {mapping_id} を検索中")

    # SQLiteモード
    if use_sqlite and Path(DEFAULT_DB_PATH).exists():
        try:
            conn = _get_db_connection(DEFAULT_DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, pattern, match_type, category, column_name as column, priority, source
                FROM store_mappings
                WHERE id = ?
            """, (mapping_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                entry = {
                    'id': row['id'],
                    'pattern': row['pattern'],
                    'match_type': row['match_type'],
                    'category': row['category'],
                    'column': row['column'],
                    'priority': row['priority']
                }
                logger.info(f"マッピングID {mapping_id} が見つかりました（SQLite）")
                return entry
            else:
                logger.warning(f"マッピングID {mapping_id} が見つかりませんでした（SQLite）")
                return None

        except Exception as e:
            logger.error(f"SQLiteからのマッピング取得に失敗: {str(e)}")
            # フォールバック

    # JSONモード（フォールバック）
    mappings = get_all_mappings(use_sqlite=False)
    for entry in mappings:
        if entry.get('id') == mapping_id:
            logger.info(f"マッピングID {mapping_id} が見つかりました（JSON）")
            return entry

    logger.warning(f"マッピングID {mapping_id} が見つかりませんでした")
    return None


def get_next_id(use_sqlite: bool = True) -> int:
    """
    次のマッピングIDを生成する

    Args:
        use_sqlite (bool): SQLiteを使用するか（デフォルト: True）

    Returns:
        int: 次のID（最大ID + 1）。エントリがない場合は1

    Example:
        >>> get_next_id()
        3

    Note:
        SQLiteモードではAUTOINCREMENTが自動的にIDを生成するため、
        この関数はJSONモードでのみ使用されます。
    """
    logger.info("次のIDを生成中")

    # SQLiteモード（AUTOINCREMENTにより自動採番されるため不要）
    if use_sqlite and Path(DEFAULT_DB_PATH).exists():
        try:
            conn = _get_db_connection(DEFAULT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) as max_id FROM store_mappings")
            result = cursor.fetchone()
            conn.close()

            max_id = result['max_id'] if result['max_id'] is not None else 0
            next_id = max_id + 1
            logger.info(f"次のID: {next_id} を生成しました（SQLite）")
            return next_id

        except Exception as e:
            logger.error(f"SQLiteからの次ID取得に失敗: {str(e)}")
            # フォールバック

    # JSONモード
    mappings = get_all_mappings(use_sqlite=False)
    if not mappings:
        logger.info("マッピングが空のため、ID 1 を返却")
        return 1

    max_id = max(entry.get('id', 0) for entry in mappings)
    next_id = max_id + 1
    logger.info(f"次のID: {next_id} を生成しました（JSON）")
    return next_id


def add_mapping(entry: Dict, use_sqlite: bool = True) -> MappingEntry:
    """
    新規マッピングエントリを追加する

    Args:
        entry (Dict): 追加するマッピングエントリ（IDは自動採番）
            必須フィールド:
                - pattern (str): 店舗名パターン
                - match_type (str): 一致方法(exact, startswith, contains, keyword)
                - category (str): カテゴリ名
                - column (str): 列番号(C～V)
                - priority (int): 優先順位(1～4)
            オプショナルフィールド:
                - note (str): 備考
        use_sqlite (bool): SQLiteを使用するか（デフォルト: True）

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

    # SQLiteモード
    if use_sqlite and Path(DEFAULT_DB_PATH).exists():
        try:
            # 基本バリデーション（ID不要）
            pattern = entry.get('pattern')
            match_type = entry.get('match_type')
            category = entry.get('category')
            column = entry.get('column')
            priority = entry.get('priority', 1)
            source = entry.get('source', 'manual')

            # 必須フィールドチェック
            if not all([pattern, match_type, category, column]):
                raise MappingValidationError(
                    "必須フィールドが不足しています",
                    details={'entry': entry}
                )

            # データベース接続
            conn = _get_db_connection(DEFAULT_DB_PATH)
            cursor = conn.cursor()

            # トランザクション開始
            conn.execute("BEGIN TRANSACTION")

            try:
                # INSERT実行（column -> column_name）
                cursor.execute("""
                    INSERT INTO store_mappings (pattern, match_type, category, column_name, priority, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (pattern, match_type, category, column, priority, source))

                # 挿入されたIDを取得
                new_id = cursor.lastrowid

                # コミット
                conn.commit()

                # 挿入されたレコードを取得
                cursor.execute("""
                    SELECT id, pattern, match_type, category, column_name as column, priority, source
                    FROM store_mappings
                    WHERE id = ?
                """, (new_id,))

                row = cursor.fetchone()
                conn.close()

                new_entry = {
                    'id': row['id'],
                    'pattern': row['pattern'],
                    'match_type': row['match_type'],
                    'category': row['category'],
                    'column': row['column'],
                    'priority': row['priority']
                }

                logger.info(f"[CRUD:ADD] マッピング追加成功（SQLite） - ID={new_id}, "
                           f"pattern='{new_entry['pattern']}', category='{new_entry['category']}'")
                return new_entry

            except sqlite3.IntegrityError as e:
                conn.rollback()
                conn.close()
                # UNIQUE制約違反（pattern重複）
                logger.warning(f"[CRUD:ADD] 重複エラー - pattern='{pattern}': {str(e)}")
                raise DuplicateMappingError(
                    f"同じpatternが既に存在します: {pattern}",
                    details={'pattern': pattern, 'error': str(e)}
                )

        except DuplicateMappingError:
            raise
        except Exception as e:
            logger.error(f"SQLiteへのマッピング追加に失敗: {str(e)}")
            # フォールバックしてJSONに保存
            logger.warning("JSONファイルへの保存を試みます")

    # JSONモード（フォールバック）
    mapping_data = load_mapping_data(DEFAULT_MAPPING_PATH)
    mappings = mapping_data.get('mappings', [])

    # 次のIDを生成
    next_id = get_next_id(use_sqlite=False)

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

    logger.info(f"[CRUD:ADD] マッピング追加成功（JSON） - ID={next_id}, pattern='{new_entry['pattern']}', "
                f"category='{new_entry['category']}', 総件数={len(mappings)}件")
    return new_entry


def update_mapping(mapping_id: int, entry: Dict, use_sqlite: bool = True) -> MappingEntry:
    """
    マッピングエントリを更新する

    Args:
        mapping_id (int): 更新対象のマッピングID
        entry (Dict): 更新内容（部分更新対応）
        use_sqlite (bool): SQLiteを使用するか（デフォルト: True）

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

    # SQLiteモード
    if use_sqlite and Path(DEFAULT_DB_PATH).exists():
        try:
            conn = _get_db_connection(DEFAULT_DB_PATH)
            cursor = conn.cursor()

            # 既存レコードを取得
            cursor.execute("""
                SELECT id, pattern, match_type, category, column_name, priority, source
                FROM store_mappings
                WHERE id = ?
            """, (mapping_id,))

            row = cursor.fetchone()

            if not row:
                conn.close()
                logger.warning(f"[CRUD:UPDATE] 更新対象が見つかりません（SQLite） - ID={mapping_id}")
                raise MappingNotFoundError(
                    f"ID {mapping_id} のマッピングが見つかりません",
                    details={'mapping_id': mapping_id}
                )

            # 現在の値を取得
            current = dict(row)
            logger.debug(f"[CRUD:UPDATE] 更新前 - ID={mapping_id}, pattern='{current['pattern']}', "
                        f"category='{current['category']}', priority={current['priority']}")

            # 更新値をマージ（column -> column_name変換）
            updates = {}
            if 'pattern' in entry:
                updates['pattern'] = entry['pattern']
            if 'match_type' in entry:
                updates['match_type'] = entry['match_type']
            if 'category' in entry:
                updates['category'] = entry['category']
            if 'column' in entry:
                updates['column_name'] = entry['column']
            if 'priority' in entry:
                updates['priority'] = entry['priority']
            if 'source' in entry:
                updates['source'] = entry['source']

            # 更新項目がない場合
            if not updates:
                conn.close()
                logger.warning(f"[CRUD:UPDATE] 更新項目がありません - ID={mapping_id}")
                return {
                    'id': current['id'],
                    'pattern': current['pattern'],
                    'match_type': current['match_type'],
                    'category': current['category'],
                    'column': current['column_name'],
                    'priority': current['priority']
                }

            # トランザクション開始
            conn.execute("BEGIN TRANSACTION")

            try:
                # UPDATE実行（updated_atは自動更新）
                set_clauses = [f"{key} = ?" for key in updates.keys()]
                sql = f"UPDATE store_mappings SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(sql, list(updates.values()) + [mapping_id])

                # コミット
                conn.commit()

                # 更新後のレコードを取得
                cursor.execute("""
                    SELECT id, pattern, match_type, category, column_name as column, priority, source
                    FROM store_mappings
                    WHERE id = ?
                """, (mapping_id,))

                row = cursor.fetchone()
                conn.close()

                updated_entry = {
                    'id': row['id'],
                    'pattern': row['pattern'],
                    'match_type': row['match_type'],
                    'category': row['category'],
                    'column': row['column'],
                    'priority': row['priority']
                }

                logger.info(f"[CRUD:UPDATE] マッピング更新成功（SQLite） - ID={mapping_id}, "
                           f"pattern='{updated_entry['pattern']}', category='{updated_entry['category']}', "
                           f"priority={updated_entry['priority']}")
                return updated_entry

            except sqlite3.IntegrityError as e:
                conn.rollback()
                conn.close()
                logger.warning(f"[CRUD:UPDATE] 重複エラー - ID={mapping_id}: {str(e)}")
                raise DuplicateMappingError(
                    f"同じpatternが既に存在します",
                    details={'mapping_id': mapping_id, 'error': str(e)}
                )

        except MappingNotFoundError:
            raise
        except DuplicateMappingError:
            raise
        except Exception as e:
            logger.error(f"SQLiteでのマッピング更新に失敗: {str(e)}")
            # フォールバック

    # JSONモード（フォールバック）
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
        logger.warning(f"[CRUD:UPDATE] 更新対象が見つかりません（JSON） - ID={mapping_id}")
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

    logger.info(f"[CRUD:UPDATE] マッピング更新成功（JSON） - ID={mapping_id}, pattern='{updated_entry['pattern']}', "
                f"category='{updated_entry['category']}', priority={updated_entry['priority']}")
    return updated_entry


def delete_mapping(mapping_id: int, use_sqlite: bool = True) -> bool:
    """
    マッピングエントリを削除する

    Args:
        mapping_id (int): 削除対象のマッピングID
        use_sqlite (bool): SQLiteを使用するか（デフォルト: True）

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

    # SQLiteモード
    if use_sqlite and Path(DEFAULT_DB_PATH).exists():
        try:
            conn = _get_db_connection(DEFAULT_DB_PATH)
            cursor = conn.cursor()

            # 削除前のレコードを取得（監査用）
            cursor.execute("""
                SELECT id, pattern, category, match_type
                FROM store_mappings
                WHERE id = ?
            """, (mapping_id,))

            row = cursor.fetchone()

            if not row:
                conn.close()
                logger.warning(f"[CRUD:DELETE] 削除対象が見つかりません（SQLite） - ID={mapping_id}")
                raise MappingNotFoundError(
                    f"ID {mapping_id} のマッピングが見つかりません",
                    details={'mapping_id': mapping_id}
                )

            target_entry = dict(row)
            logger.debug(f"[CRUD:DELETE] 削除対象 - ID={mapping_id}, pattern='{target_entry['pattern']}', "
                        f"category='{target_entry['category']}', match_type={target_entry['match_type']}")

            # トランザクション開始
            conn.execute("BEGIN TRANSACTION")

            try:
                # DELETE実行
                cursor.execute("DELETE FROM store_mappings WHERE id = ?", (mapping_id,))

                # コミット
                conn.commit()
                conn.close()

                logger.info(f"[CRUD:DELETE] マッピング削除成功（SQLite） - ID={mapping_id}, "
                           f"pattern='{target_entry['pattern']}'")
                return True

            except Exception as e:
                conn.rollback()
                conn.close()
                logger.error(f"[CRUD:DELETE] 削除処理でエラーが発生: {str(e)}")
                raise MappingSaveError(
                    f"マッピングの削除に失敗しました: {str(e)}",
                    details={'mapping_id': mapping_id, 'error': str(e)}
                )

        except MappingNotFoundError:
            raise
        except Exception as e:
            logger.error(f"SQLiteでのマッピング削除に失敗: {str(e)}")
            # フォールバック

    # JSONモード（フォールバック）
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
        logger.warning(f"[CRUD:DELETE] 削除対象が見つかりません（JSON） - ID={mapping_id}")
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

    logger.info(f"[CRUD:DELETE] マッピング削除成功（JSON） - ID={mapping_id}, pattern='{target_entry.get('pattern')}', "
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
        - バックアップは data/backups/ ディレクトリに保存
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

        # Windowsではロック中のファイルを置換できないため、置換前にロックを解放
        if platform.system() == 'Windows' and lock_file is not None:
            try:
                lock_file.close()
                lock_file = None
                logger.debug("置換前にファイルロックを解放しました（Windows）")
            except Exception as e:
                logger.error(f"ファイルロック解放エラー（Windows）: {str(e)}")
                raise MappingSaveError(
                    f"ファイルロックの解放に失敗しました: {str(e)}",
                    details={'path': str(file_path), 'error': str(e), 'os': 'Windows'}
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


# ==================== モジュール初期化 ====================

# モジュールロード時にデータベースを自動初期化
try:
    ensure_database_initialized()
except Exception as e:
    logger.warning(f"データベース自動初期化をスキップしました: {str(e)}")
