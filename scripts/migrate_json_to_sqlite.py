"""
JSON to SQLite Migration Script

このスクリプトは data/mapping.json のマッピングデータを
SQLite データベース (data/mappings.db) に移行します。

主な機能:
- data/mapping.json からマッピングデータを読み込み
- data/mappings.db を作成・初期化
- 全マッピングを SQLite テーブルに INSERT
- 移行前に自動バックアップを作成
- トランザクション処理（全件成功 or 全件ロールバック）
- 重複チェック（pattern の一意性検証）

使用例:
    # 基本的な使い方
    python scripts/migrate_json_to_sqlite.py

    # カスタムパス指定
    python scripts/migrate_json_to_sqlite.py --json-path custom/mapping.json --db-path custom/mappings.db
"""

import json
import sqlite3
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import shutil

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.mapping_manager import init_database, MappingSaveError
from modules.category_logic import (
    MATCH_TYPE_EXACT,
    MATCH_TYPE_STARTSWITH,
    MATCH_TYPE_CONTAINS,
    MATCH_TYPE_KEYWORD
)

# ==================== ロガー設定 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 定数 ====================

DEFAULT_JSON_PATH = 'data/mapping.json'
DEFAULT_DB_PATH = 'data/mappings.db'
BACKUP_DIR = 'data/backups'

# match_type から priority への変換マップ
MATCH_TYPE_PRIORITY_MAP = {
    MATCH_TYPE_EXACT: 1,
    MATCH_TYPE_STARTSWITH: 2,
    MATCH_TYPE_CONTAINS: 3,
    MATCH_TYPE_KEYWORD: 4
}


# ==================== ヘルパー関数 ====================

def create_backup(json_path: str) -> Optional[str]:
    """
    JSONファイルのバックアップを作成する

    Args:
        json_path (str): バックアップ対象のJSONファイルパス

    Returns:
        Optional[str]: バックアップファイルパス（失敗時はNone）
    """
    json_file = Path(json_path)

    if not json_file.exists():
        logger.warning(f"バックアップ対象ファイルが見つかりません: {json_path}")
        return None

    try:
        # バックアップディレクトリ作成
        backup_dir = Path(BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)

        # タイムスタンプ付きバックアップファイル名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"mapping_backup_{timestamp}.json"

        # ファイルコピー
        shutil.copy2(json_file, backup_file)
        logger.info(f"バックアップを作成しました: {backup_file}")

        return str(backup_file)

    except Exception as e:
        logger.error(f"バックアップ作成に失敗しました: {str(e)}")
        return None


def load_json_mappings(json_path: str) -> Dict:
    """
    JSONファイルからマッピングデータを読み込む

    Args:
        json_path (str): JSONファイルパス

    Returns:
        Dict: マッピングデータ

    Raises:
        FileNotFoundError: ファイルが存在しない
        json.JSONDecodeError: JSON形式が不正
    """
    json_file = Path(json_path)

    if not json_file.exists():
        raise FileNotFoundError(f"JSONファイルが見つかりません: {json_path}")

    with json_file.open('r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"JSONファイルを読み込みました: {json_path} ({len(data.get('mappings', []))}件)")
    return data


def convert_column_name(column: str) -> str:
    """
    column フィールドを column_name に変換する

    Args:
        column (str): 元の列名（例: "B", "C"）

    Returns:
        str: 変換後の列名（そのまま返す）

    Note:
        フィールド名が変わっただけで値は同じ
    """
    return column


def calculate_priority(match_type: str, existing_priority: Optional[int] = None) -> int:
    """
    match_type から priority を自動導出する

    Args:
        match_type (str): マッチタイプ（exact, startswith, contains, keyword）
        existing_priority (Optional[int]): 既存の priority 値（存在する場合）

    Returns:
        int: 優先順位（1～4）

    Note:
        既存の priority が有効範囲（1～4）の場合はそれを優先する
        それ以外は match_type から自動導出
    """
    # 既存の priority が有効範囲なら使用
    if existing_priority is not None and 1 <= existing_priority <= 4:
        return existing_priority

    # match_type から priority を導出
    return MATCH_TYPE_PRIORITY_MAP.get(match_type, 4)


def migrate_mappings(json_data: Dict, db_path: str) -> int:
    """
    JSONデータをSQLiteデータベースに移行する

    Args:
        json_data (Dict): JSONマッピングデータ
        db_path (str): SQLiteデータベースパス

    Returns:
        int: 移行件数

    Raises:
        sqlite3.Error: データベースエラー
    """
    mappings = json_data.get('mappings', [])

    if not mappings:
        logger.warning("移行対象のマッピングが存在しません")
        return 0

    logger.info(f"移行処理を開始します: {len(mappings)}件")

    conn = None
    try:
        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # トランザクション開始（明示的）
        conn.execute("BEGIN TRANSACTION")

        migrated_count = 0
        skipped_count = 0

        for index, entry in enumerate(mappings, start=1):
            pattern = entry.get('pattern')
            match_type = entry.get('match_type')
            category = entry.get('category')
            column = entry.get('column')
            existing_priority = entry.get('priority')

            # 必須フィールドチェック
            if not all([pattern, match_type, category, column]):
                logger.warning(f"[{index}/{len(mappings)}] スキップ - 必須フィールド不足: {entry}")
                skipped_count += 1
                continue

            # column_name に変換
            column_name = convert_column_name(column)

            # priority 自動導出
            priority = calculate_priority(match_type, existing_priority)

            # 列名の検証（C～V）
            if not (len(column_name) == 1 and 'C' <= column_name <= 'V'):
                logger.warning(f"[{index}/{len(mappings)}] スキップ - 不正な列名: {column_name}")
                skipped_count += 1
                continue

            try:
                # INSERT実行
                cursor.execute("""
                    INSERT INTO store_mappings (pattern, match_type, category, column_name, priority, source)
                    VALUES (?, ?, ?, ?, ?, 'manual')
                """, (pattern, match_type, category, column_name, priority))

                migrated_count += 1
                logger.debug(f"[{migrated_count}/{len(mappings)}] 移行成功: pattern={pattern}, category={category}, column={column_name}, priority={priority}")

            except sqlite3.IntegrityError as e:
                # UNIQUE制約違反（pattern重複）
                logger.warning(f"[{index}/{len(mappings)}] スキップ - 重複パターン: pattern={pattern}, error={str(e)}")
                skipped_count += 1
                continue

        # トランザクションコミット
        conn.commit()

        logger.info(f"移行処理が完了しました: 成功={migrated_count}件, スキップ={skipped_count}件")
        return migrated_count

    except sqlite3.Error as e:
        # エラー時はロールバック
        if conn:
            conn.rollback()
        logger.error(f"データベースエラーが発生しました: {str(e)}")
        raise

    except Exception as e:
        # 予期しないエラー時もロールバック
        if conn:
            conn.rollback()
        logger.error(f"予期しないエラーが発生しました: {str(e)}")
        raise

    finally:
        if conn:
            conn.close()


def verify_migration(db_path: str) -> Dict:
    """
    移行結果を検証する

    Args:
        db_path (str): SQLiteデータベースパス

    Returns:
        Dict: 検証結果
            {
                'total_count': int,
                'manual_count': int,
                'auto_count': int,
                'sample_records': List[Dict]
            }
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 総件数
    cursor.execute("SELECT COUNT(*) as count FROM store_mappings")
    total_count = cursor.fetchone()['count']

    # source別件数
    cursor.execute("SELECT COUNT(*) as count FROM store_mappings WHERE source = 'manual'")
    manual_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM store_mappings WHERE source = 'auto'")
    auto_count = cursor.fetchone()['count']

    # サンプルレコード（最初の5件）
    cursor.execute("""
        SELECT id, pattern, match_type, category, column_name, priority, source, created_at
        FROM store_mappings
        ORDER BY id
        LIMIT 5
    """)
    sample_records = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        'total_count': total_count,
        'manual_count': manual_count,
        'auto_count': auto_count,
        'sample_records': sample_records
    }


# ==================== メイン処理 ====================

def main():
    """
    メイン処理

    JSONからSQLiteへの移行を実行します。
    """
    import argparse

    # コマンドライン引数パース
    parser = argparse.ArgumentParser(description='Migrate mapping data from JSON to SQLite')
    parser.add_argument('--json-path', default=DEFAULT_JSON_PATH, help='Input JSON file path')
    parser.add_argument('--db-path', default=DEFAULT_DB_PATH, help='Output SQLite database path')
    parser.add_argument('--skip-backup', action='store_true', help='Skip backup creation')

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("JSON to SQLite Migration Script")
    logger.info("=" * 60)
    logger.info(f"JSON Path: {args.json_path}")
    logger.info(f"DB Path: {args.db_path}")
    logger.info("=" * 60)

    try:
        # Step 1: バックアップ作成
        if not args.skip_backup:
            logger.info("[Step 1] バックアップ作成中...")
            backup_path = create_backup(args.json_path)
            if backup_path:
                logger.info(f"✓ バックアップ作成成功: {backup_path}")
            else:
                logger.warning("⚠ バックアップ作成をスキップしました")
        else:
            logger.info("[Step 1] バックアップ作成をスキップしました")

        # Step 2: JSONファイル読み込み
        logger.info("[Step 2] JSONファイル読み込み中...")
        json_data = load_json_mappings(args.json_path)
        logger.info(f"✓ JSONファイル読み込み成功: {len(json_data.get('mappings', []))}件")

        # Step 3: データベース初期化
        logger.info("[Step 3] データベース初期化中...")
        init_database(args.db_path)
        logger.info(f"✓ データベース初期化成功: {args.db_path}")

        # Step 4: マッピング移行
        logger.info("[Step 4] マッピング移行中...")
        migrated_count = migrate_mappings(json_data, args.db_path)
        logger.info(f"✓ マッピング移行成功: {migrated_count}件")

        # Step 5: 移行結果検証
        logger.info("[Step 5] 移行結果検証中...")
        verification = verify_migration(args.db_path)
        logger.info(f"✓ 移行結果検証成功:")
        logger.info(f"  - 総件数: {verification['total_count']}件")
        logger.info(f"  - 手動登録: {verification['manual_count']}件")
        logger.info(f"  - 自動登録: {verification['auto_count']}件")

        # サンプルレコード表示
        if verification['sample_records']:
            logger.info("  - サンプルレコード（最初の5件）:")
            for record in verification['sample_records']:
                logger.info(f"    ID={record['id']}: pattern={record['pattern']}, "
                           f"category={record['category']}, column={record['column_name']}, "
                           f"priority={record['priority']}, source={record['source']}")

        logger.info("=" * 60)
        logger.info("✓ 移行処理が正常に完了しました")
        logger.info("=" * 60)

    except FileNotFoundError as e:
        logger.error(f"✗ ファイルが見つかりません: {str(e)}")
        sys.exit(1)

    except json.JSONDecodeError as e:
        logger.error(f"✗ JSON解析エラー: {str(e)}")
        sys.exit(1)

    except sqlite3.Error as e:
        logger.error(f"✗ データベースエラー: {str(e)}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"✗ 予期しないエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
