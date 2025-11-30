#!/usr/bin/env python3
"""
Phase 2 マッピングデータ読込・検証機能のテストスクリプト

このスクリプトは以下のテストケースを実行します:
1. 正常系: config/mapping.jsonの読み込み・検証成功
2. 異常系1: ファイルが存在しない場合にMappingLoadError
3. 異常系2: JSONが不正な場合にInvalidMappingFormatError
4. 異常系3: 必須フィールドが不足している場合にMappingValidationError
5. 異常系4: match_typeが不正な場合にMappingValidationError
"""

import sys
import json
import tempfile
from pathlib import Path

# モジュールのインポート
from modules.category_logic import (
    load_mapping_data,
    validate_mapping_entry,
    validate_mapping_data,
    MappingLoadError,
    MappingValidationError,
    InvalidMappingFormatError
)


def test_normal_case():
    """テストケース1: 正常系 - config/mapping.jsonの読み込み・検証成功"""
    print("\n[テスト1] 正常系: config/mapping.jsonの読み込み・検証")
    print("-" * 60)

    try:
        # マッピングデータ読み込み
        data = load_mapping_data('config/mapping.json')
        print(f"✓ ファイル読み込み成功")
        print(f"  - バージョン: {data['version']}")
        print(f"  - マッピング数: {len(data['mappings'])}件")

        # データ全体を検証
        validate_mapping_data(data)
        print(f"✓ データ検証成功")

        # 各エントリの詳細表示
        print(f"\n  マッピングエントリ:")
        for entry in data['mappings']:
            print(f"    - ID {entry['id']}: {entry['pattern']} → {entry['category']} (列{entry['column']})")

        print(f"\n  デフォルト設定:")
        print(f"    - カテゴリ: {data['default']['category']}")
        print(f"    - 列: {data['default']['column']}")

        return True
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        return False


def test_file_not_found():
    """テストケース2: 異常系 - ファイルが存在しない場合"""
    print("\n[テスト2] 異常系: ファイル不存在エラー")
    print("-" * 60)

    try:
        load_mapping_data('config/non_existent_file.json')
        print("✗ テスト失敗: 例外が発生しませんでした")
        return False
    except MappingLoadError as e:
        print(f"✓ 期待通りMappingLoadErrorが発生")
        print(f"  - メッセージ: {e.message}")
        print(f"  - 詳細: {e.details}")
        return True
    except Exception as e:
        print(f"✗ テスト失敗: 予期しない例外が発生: {type(e).__name__}: {e}")
        return False


def test_invalid_json():
    """テストケース3: 異常系 - JSONが不正な場合"""
    print("\n[テスト3] 異常系: JSON形式エラー")
    print("-" * 60)

    # 一時ファイル作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{ invalid json content }")
        temp_file = f.name

    try:
        load_mapping_data(temp_file)
        print("✗ テスト失敗: 例外が発生しませんでした")
        return False
    except InvalidMappingFormatError as e:
        print(f"✓ 期待通りInvalidMappingFormatErrorが発生")
        print(f"  - メッセージ: {e.message}")
        return True
    except Exception as e:
        print(f"✗ テスト失敗: 予期しない例外が発生: {type(e).__name__}: {e}")
        return False
    finally:
        # 一時ファイル削除
        Path(temp_file).unlink(missing_ok=True)


def test_missing_fields():
    """テストケース4: 異常系 - 必須フィールド不足"""
    print("\n[テスト4] 異常系: 必須フィールド不足エラー")
    print("-" * 60)

    # versionフィールドが不足しているデータ
    invalid_data = {
        "mappings": [
            {
                "id": 1,
                "pattern": "テスト",
                "match_type": "exact",
                "category": "テストカテゴリ",
                "column": "C",
                "priority": 1
            }
        ],
        "default": {
            "category": "支払額",
            "column": "B"
        }
    }

    # 一時ファイル作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_data, f, ensure_ascii=False, indent=2)
        temp_file = f.name

    try:
        load_mapping_data(temp_file)
        print("✗ テスト失敗: 例外が発生しませんでした")
        return False
    except MappingValidationError as e:
        print(f"✓ 期待通りMappingValidationErrorが発生")
        print(f"  - メッセージ: {e.message}")
        print(f"  - 詳細: {e.details}")
        return True
    except Exception as e:
        print(f"✗ テスト失敗: 予期しない例外が発生: {type(e).__name__}: {e}")
        return False
    finally:
        # 一時ファイル削除
        Path(temp_file).unlink(missing_ok=True)


def test_invalid_match_type():
    """テストケース5: 異常系 - match_typeが不正"""
    print("\n[テスト5] 異常系: match_type不正エラー")
    print("-" * 60)

    # 不正なmatch_typeを持つエントリ
    invalid_entry = {
        "id": 1,
        "pattern": "テスト",
        "match_type": "invalid_type",  # 不正な値
        "category": "テストカテゴリ",
        "column": "C",
        "priority": 1
    }

    try:
        validate_mapping_entry(invalid_entry)
        print("✗ テスト失敗: 例外が発生しませんでした")
        return False
    except MappingValidationError as e:
        print(f"✓ 期待通りMappingValidationErrorが発生")
        print(f"  - メッセージ: {e.message}")
        print(f"  - 詳細: {e.details}")
        return True
    except Exception as e:
        print(f"✗ テスト失敗: 予期しない例外が発生: {type(e).__name__}: {e}")
        return False


def test_invalid_column():
    """追加テスト: columnが不正"""
    print("\n[追加テスト] 異常系: column不正エラー")
    print("-" * 60)

    # 不正なcolumnを持つエントリ
    invalid_entry = {
        "id": 1,
        "pattern": "テスト",
        "match_type": "exact",
        "category": "テストカテゴリ",
        "column": "Z",  # 不正な値（有効範囲はB～V）
        "priority": 1
    }

    try:
        validate_mapping_entry(invalid_entry)
        print("✗ テスト失敗: 例外が発生しませんでした")
        return False
    except MappingValidationError as e:
        print(f"✓ 期待通りMappingValidationErrorが発生")
        print(f"  - メッセージ: {e.message}")
        return True
    except Exception as e:
        print(f"✗ テスト失敗: 予期しない例外が発生: {type(e).__name__}: {e}")
        return False


def test_invalid_priority():
    """追加テスト: priorityが範囲外"""
    print("\n[追加テスト] 異常系: priority範囲外エラー")
    print("-" * 60)

    # 不正なpriorityを持つエントリ
    invalid_entry = {
        "id": 1,
        "pattern": "テスト",
        "match_type": "exact",
        "category": "テストカテゴリ",
        "column": "C",
        "priority": 5  # 不正な値（有効範囲は1～4）
    }

    try:
        validate_mapping_entry(invalid_entry)
        print("✗ テスト失敗: 例外が発生しませんでした")
        return False
    except MappingValidationError as e:
        print(f"✓ 期待通りMappingValidationErrorが発生")
        print(f"  - メッセージ: {e.message}")
        return True
    except Exception as e:
        print(f"✗ テスト失敗: 予期しない例外が発生: {type(e).__name__}: {e}")
        return False


def main():
    """メイン関数 - すべてのテストを実行"""
    print("=" * 60)
    print("Phase 2 マッピングデータ読込・検証機能テスト")
    print("=" * 60)

    results = []

    # 各テストケースを実行
    results.append(("正常系: データ読み込み・検証", test_normal_case()))
    results.append(("異常系: ファイル不存在", test_file_not_found()))
    results.append(("異常系: JSON形式エラー", test_invalid_json()))
    results.append(("異常系: 必須フィールド不足", test_missing_fields()))
    results.append(("異常系: match_type不正", test_invalid_match_type()))
    results.append(("異常系: column不正", test_invalid_column()))
    results.append(("異常系: priority範囲外", test_invalid_priority()))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n合計: {passed}/{total} テスト成功")

    # 終了コード
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
