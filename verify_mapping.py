#!/usr/bin/env python3
"""
config/mapping.jsonを使用した動作確認スクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from modules.category_logic import (
    load_mapping_data,
    validate_mapping_data,
    determine_category,
    detect_unregistered_stores,
    MappingValidationError,
    MappingLoadError,
    InvalidMappingFormatError
)


def test_load_mapping():
    """1.1 load_mapping_data()の動作確認"""
    print("=" * 60)
    print("1.1 load_mapping_data() 動作確認")
    print("=" * 60)

    try:
        data = load_mapping_data('config/mapping.json')
        print("✓ config/mapping.jsonを正常に読み込みました")
        print(f"  - バージョン: {data['version']}")
        print(f"  - マッピング数: {len(data['mappings'])}")
        print(f"  - デフォルトカテゴリ: {data['default']['category']}")
        print(f"  - デフォルト列: {data['default']['column']}")
        print()

        # マッピングエントリの詳細を表示
        print("マッピングエントリ:")
        for entry in data['mappings']:
            print(f"  - ID={entry['id']}: {entry['pattern']} ({entry['match_type']}) → {entry['category']} ({entry['column']}列)")
        print()

        # バリデーション実行
        print("データバリデーション実行...")
        validate_mapping_data(data)
        print("✓ バリデーション成功")
        print()

        return data

    except (MappingLoadError, InvalidMappingFormatError, MappingValidationError) as e:
        print(f"✗ エラー: {e.message}")
        print(f"  詳細: {e.details}")
        return None


def test_determine_category(mapping_data):
    """1.2 determine_category()の動作確認"""
    print("=" * 60)
    print("1.2 determine_category() 動作確認")
    print("=" * 60)

    # テストケース
    test_cases = [
        ("ユシンヤ", True, "外食費", "C"),  # 部分一致でマッチする
        ("AMAZON", True, "日用品費", "D"),  # 部分一致でマッチする
        ("ユシンヤ池袋店", True, "外食費", "C"),  # 部分一致でマッチする
        ("AMAZON.CO.JP", True, "日用品費", "D"),  # 部分一致でマッチする
        ("未登録店舗", False, "支払額", "B"),  # マッチしない（デフォルト値）
        ("スターバックス", False, "支払額", "B"),  # マッチしない（デフォルト値）
    ]

    success_count = 0
    for store, expected_matched, expected_category, expected_column in test_cases:
        result = determine_category(store, mapping_data)

        # 検証
        is_success = (
            result['matched'] == expected_matched and
            result['category'] == expected_category and
            result['column'] == expected_column
        )

        status = "✓" if is_success else "✗"
        if is_success:
            success_count += 1

        print(f"{status} 店舗名: {store}")
        print(f"  - マッチ: {result['matched']} (期待: {expected_matched})")
        print(f"  - カテゴリ: {result['category']} (期待: {expected_category})")
        print(f"  - 列: {result['column']} (期待: {expected_column})")
        if result['matched']:
            print(f"  - パターン: {result['pattern']}")
            print(f"  - マッチタイプ: {result['match_type']}")
        print()

    print(f"成功: {success_count}/{len(test_cases)}")
    print()
    return success_count == len(test_cases)


def test_detect_unregistered_stores(mapping_data):
    """1.3 detect_unregistered_stores()の動作確認"""
    print("=" * 60)
    print("1.3 detect_unregistered_stores() 動作確認")
    print("=" * 60)

    # テストレコード
    records = [
        {'store': 'ユシンヤ', 'amount': 5000},
        {'store': 'AMAZON', 'amount': 3000},
        {'store': '未登録店舗A', 'amount': 2000},
        {'store': '未登録店舗A', 'amount': 1000},
        {'store': '未登録店舗B', 'amount': 500},
        {'store': 'ユシンヤ池袋店', 'amount': 8000},
        {'store': '未登録店舗C', 'amount': 10000},
    ]

    result = detect_unregistered_stores(records, mapping_data)

    print(f"検出された未登録店舗数: {len(result)}")
    print()

    if result:
        print("未登録店舗リスト（金額降順）:")
        for item in result:
            print(f"  - {item['store']}: {item['count']}回, 合計{item['total_amount']}円")
        print()

        # ソート順の確認
        amounts = [item['total_amount'] for item in result]
        is_sorted = all(amounts[i] >= amounts[i+1] for i in range(len(amounts)-1))

        if is_sorted:
            print("✓ 金額降順でソートされています")
        else:
            print("✗ ソート順が正しくありません")
        print()

        # 合計金額の確認
        expected_total = 2000 + 1000 + 500 + 10000  # 未登録店舗の合計
        actual_total = sum(item['total_amount'] for item in result)

        if expected_total == actual_total:
            print(f"✓ 合計金額が正しいです: {actual_total}円")
        else:
            print(f"✗ 合計金額が異なります: 期待{expected_total}円, 実際{actual_total}円")

        return is_sorted and (expected_total == actual_total)
    else:
        print("✗ 未登録店舗が検出されませんでした")
        return False


def main():
    """メイン処理"""
    print()
    print("config/mapping.json 統合動作確認")
    print()

    # 1.1 マッピングデータ読み込み
    mapping_data = test_load_mapping()
    if not mapping_data:
        print("マッピングデータの読み込みに失敗しました")
        return False

    # 1.2 カテゴリ判定テスト
    test1_success = test_determine_category(mapping_data)

    # 1.3 未登録店舗検出テスト
    test2_success = test_detect_unregistered_stores(mapping_data)

    # 総合結果
    print("=" * 60)
    print("総合結果")
    print("=" * 60)
    print(f"1.1 load_mapping_data(): {'✓ PASS' if mapping_data else '✗ FAIL'}")
    print(f"1.2 determine_category(): {'✓ PASS' if test1_success else '✗ FAIL'}")
    print(f"1.3 detect_unregistered_stores(): {'✓ PASS' if test2_success else '✗ FAIL'}")
    print()

    all_success = mapping_data and test1_success and test2_success
    if all_success:
        print("✓ すべてのテストが成功しました")
    else:
        print("✗ 一部のテストが失敗しました")
    print()

    return all_success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
