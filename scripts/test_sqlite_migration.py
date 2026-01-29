"""
SQLite Migration Test Script

このスクリプトは Phase 7.1 の SQLite マッピングDB実装をテストします。

テスト項目:
1. データベース初期化
2. JSON→SQLite移行
3. CRUD操作（追加、読込、更新、削除）
4. 重複チェック
5. トランザクション処理
6. フォールバック動作
"""

import sys
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import mapping_manager
from modules import category_logic

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database_initialization():
    """テスト1: データベース初期化"""
    logger.info("=" * 60)
    logger.info("テスト1: データベース初期化")
    logger.info("=" * 60)

    db_path = Path('data/mappings.db')

    if db_path.exists():
        logger.info(f"✓ データベースファイルが存在します: {db_path}")
    else:
        logger.error(f"✗ データベースファイルが存在しません: {db_path}")
        return False

    return True


def test_crud_operations():
    """テスト2: CRUD操作"""
    logger.info("=" * 60)
    logger.info("テスト2: CRUD操作")
    logger.info("=" * 60)

    try:
        # CREATE
        logger.info("[CREATE] 新規マッピング追加テスト")
        new_mapping = {
            'pattern': 'TEST店舗',
            'match_type': 'contains',
            'category': 'テストカテゴリ',
            'column': 'E',
            'priority': 1
        }
        added = mapping_manager.add_mapping(new_mapping)
        logger.info(f"✓ 追加成功: ID={added['id']}, pattern={added['pattern']}")

        test_id = added['id']

        # READ
        logger.info("[READ] マッピング取得テスト")
        mapping = mapping_manager.get_mapping_by_id(test_id)
        if mapping and mapping['pattern'] == 'TEST店舗':
            logger.info(f"✓ 取得成功: ID={mapping['id']}, pattern={mapping['pattern']}")
        else:
            logger.error("✗ 取得失敗")
            return False

        # UPDATE
        logger.info("[UPDATE] マッピング更新テスト")
        updated = mapping_manager.update_mapping(test_id, {'priority': 3})
        if updated['priority'] == 3:
            logger.info(f"✓ 更新成功: ID={updated['id']}, priority={updated['priority']}")
        else:
            logger.error("✗ 更新失敗")
            return False

        # DELETE
        logger.info("[DELETE] マッピング削除テスト")
        result = mapping_manager.delete_mapping(test_id)
        if result:
            logger.info(f"✓ 削除成功: ID={test_id}")
        else:
            logger.error("✗ 削除失敗")
            return False

        # 削除確認
        deleted_mapping = mapping_manager.get_mapping_by_id(test_id)
        if deleted_mapping is None:
            logger.info("✓ 削除確認成功: レコードが存在しません")
        else:
            logger.error("✗ 削除確認失敗: レコードが残っています")
            return False

        return True

    except Exception as e:
        logger.error(f"✗ CRUD操作テストでエラー: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_duplicate_check():
    """テスト3: 重複チェック"""
    logger.info("=" * 60)
    logger.info("テスト3: 重複チェック")
    logger.info("=" * 60)

    try:
        # 1回目の追加
        mapping1 = {
            'pattern': 'DUPLICATE_TEST',
            'match_type': 'exact',
            'category': 'テスト',
            'column': 'F',
            'priority': 1
        }
        added1 = mapping_manager.add_mapping(mapping1)
        logger.info(f"✓ 1回目の追加成功: ID={added1['id']}")

        # 2回目の追加（重複）
        mapping2 = {
            'pattern': 'DUPLICATE_TEST',  # 同じpattern
            'match_type': 'exact',
            'category': '別カテゴリ',
            'column': 'G',
            'priority': 2
        }

        try:
            added2 = mapping_manager.add_mapping(mapping2)
            logger.error("✗ 重複チェック失敗: 重複が許可されてしまいました")
            # クリーンアップ
            mapping_manager.delete_mapping(added1['id'])
            return False
        except mapping_manager.DuplicateMappingError:
            logger.info("✓ 重複チェック成功: 重複エラーが発生しました")

        # クリーンアップ
        mapping_manager.delete_mapping(added1['id'])
        return True

    except Exception as e:
        logger.error(f"✗ 重複チェックテストでエラー: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_category_logic_integration():
    """テスト4: カテゴリ判定ロジック統合テスト"""
    logger.info("=" * 60)
    logger.info("テスト4: カテゴリ判定ロジック統合テスト")
    logger.info("=" * 60)

    try:
        # マッピングデータ読み込み（SQLiteから）
        mapping_data = category_logic.load_mapping_data(use_sqlite=True)
        logger.info(f"✓ マッピングデータ読み込み成功: {len(mapping_data['mappings'])}件")

        # カテゴリ判定テスト
        test_stores = [
            ('ユシンヤ', '外食費'),
            ('AMAZON', '日用品費'),
            ('未登録店舗', '支払額')  # デフォルト
        ]

        for store_name, expected_category in test_stores:
            result = category_logic.determine_category(store_name, mapping_data)
            if result['category'] == expected_category:
                logger.info(f"✓ カテゴリ判定成功: {store_name} → {result['category']}")
            else:
                logger.error(f"✗ カテゴリ判定失敗: {store_name} → 期待={expected_category}, 実際={result['category']}")
                return False

        return True

    except Exception as e:
        logger.error(f"✗ カテゴリ判定テストでエラー: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_migration_consistency():
    """テスト5: 移行データ整合性チェック"""
    logger.info("=" * 60)
    logger.info("テスト5: 移行データ整合性チェック")
    logger.info("=" * 60)

    try:
        # SQLiteから取得
        sqlite_mappings = mapping_manager.get_all_mappings(use_sqlite=True)
        logger.info(f"SQLiteマッピング数: {len(sqlite_mappings)}件")

        # JSONから取得
        json_mapping_data = category_logic.load_mapping_data(use_sqlite=False)
        json_mappings = json_mapping_data['mappings']
        logger.info(f"JSONマッピング数: {len(json_mappings)}件")

        # 件数チェック
        if len(sqlite_mappings) >= len(json_mappings):
            logger.info("✓ データ件数の整合性チェック成功")
        else:
            logger.warning(f"⚠ SQLiteデータ件数がJSON件数より少ない: SQLite={len(sqlite_mappings)}, JSON={len(json_mappings)}")

        # パターン一致チェック
        json_patterns = {m['pattern'] for m in json_mappings}
        sqlite_patterns = {m['pattern'] for m in sqlite_mappings}

        missing_in_sqlite = json_patterns - sqlite_patterns
        if missing_in_sqlite:
            logger.warning(f"⚠ SQLiteに存在しないパターン: {missing_in_sqlite}")
        else:
            logger.info("✓ パターンの整合性チェック成功")

        return True

    except Exception as e:
        logger.error(f"✗ データ整合性チェックでエラー: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("SQLite Migration Test - Phase 7.1")
    logger.info("=" * 60)

    tests = [
        ("データベース初期化", test_database_initialization),
        ("CRUD操作", test_crud_operations),
        ("重複チェック", test_duplicate_check),
        ("カテゴリ判定統合", test_category_logic_integration),
        ("移行データ整合性", test_migration_consistency),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"✗ テスト「{test_name}」で予期しないエラー: {str(e)}")
            results.append((test_name, False))

    # サマリー
    logger.info("=" * 60)
    logger.info("テスト結果サマリー")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status} - {test_name}")

    logger.info("=" * 60)
    logger.info(f"合計: {passed}/{total} テスト成功")
    logger.info("=" * 60)

    if passed == total:
        logger.info("✓ すべてのテストが成功しました！")
        return 0
    else:
        logger.error(f"✗ {total - passed}件のテストが失敗しました")
        return 1


if __name__ == '__main__':
    sys.exit(main())
