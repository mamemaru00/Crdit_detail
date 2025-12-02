#!/usr/bin/env python3
"""
Phase 4 実装テストスクリプト

determine_category(), detect_unregistered_stores(), determine_categories_batch()
の動作確認を実施します。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.category_logic import (
    load_mapping_data,
    determine_category,
    detect_unregistered_stores,
    determine_categories_batch
)


def print_section(title: str):
    """セクションタイトルを表示"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_determine_category():
    """determine_category() のテスト"""
    print_section("Test 1: determine_category()")

    # マッピングデータを読み込み
    mapping_data = load_mapping_data('config/mapping.json')

    # テストケース1: 登録済み店舗（完全一致）
    print("\n[テスト1-1] 登録済み店舗（完全一致）")
    result = determine_category("ユシンヤ", mapping_data)
    print(f"店舗名: ユシンヤ")
    print(f"結果: {result}")
    assert result['matched'] is True, "マッチしているべき"
    assert result['category'] == '外食費', "カテゴリは外食費であるべき"
    assert result['column'] == 'C', "列番号はCであるべき"
    print("✓ 正常動作")

    # テストケース2: 未登録店舗
    print("\n[テスト1-2] 未登録店舗")
    result = determine_category("存在しない店舗XYZ", mapping_data)
    print(f"店舗名: 存在しない店舗XYZ")
    print(f"結果: {result}")
    assert result['matched'] is False, "マッチしていないべき"
    assert result['category'] == '支払額', "デフォルトカテゴリは支払額であるべき"
    assert result['column'] == 'B', "デフォルト列はBであるべき"
    assert result['pattern'] is None, "パターンはNoneであるべき"
    assert result['match_type'] is None, "マッチタイプはNoneであるべき"
    print("✓ 正常動作")

    # テストケース3: 部分一致
    print("\n[テスト1-3] 部分一致")
    result = determine_category("東京ユシンヤ池袋店", mapping_data)
    print(f"店舗名: 東京ユシンヤ池袋店")
    print(f"結果: {result}")
    assert result['matched'] is True, "マッチしているべき"
    print("✓ 正常動作")


def test_detect_unregistered_stores():
    """detect_unregistered_stores() のテスト"""
    print_section("Test 2: detect_unregistered_stores()")

    # マッピングデータを読み込み
    mapping_data = load_mapping_data('config/mapping.json')

    # テストケース1: 未登録店舗が複数ある場合
    print("\n[テスト2-1] 未登録店舗が複数ある場合")
    records = [
        {'store': 'ユシンヤ', 'amount': 1000},  # 登録済み
        {'store': '未登録A', 'amount': 2000},    # 未登録
        {'store': '未登録A', 'amount': 3000},    # 未登録（同じ店舗）
        {'store': '未登録B', 'amount': 500},     # 未登録
        {'store': 'AMAZON', 'amount': 1500},     # 登録済み
    ]
    result = detect_unregistered_stores(records, mapping_data)
    print(f"レコード数: {len(records)}")
    print(f"未登録店舗リスト: {result}")

    assert len(result) == 2, "未登録店舗は2つであるべき"
    assert result[0]['store'] == '未登録A', "最初は未登録Aであるべき（金額降順）"
    assert result[0]['total_amount'] == 5000, "未登録Aの合計は5000であるべき"
    assert result[0]['count'] == 2, "未登録Aのカウントは2であるべき"
    assert result[1]['store'] == '未登録B', "次は未登録Bであるべき"
    assert result[1]['total_amount'] == 500, "未登録Bの合計は500であるべき"
    assert result[1]['count'] == 1, "未登録Bのカウントは1であるべき"
    print("✓ 正常動作")

    # テストケース2: 未登録店舗がない場合
    print("\n[テスト2-2] 未登録店舗がない場合")
    records = [
        {'store': 'ユシンヤ', 'amount': 1000},
        {'store': 'AMAZON', 'amount': 1500},
    ]
    result = detect_unregistered_stores(records, mapping_data)
    print(f"未登録店舗リスト: {result}")
    assert len(result) == 0, "未登録店舗は0件であるべき"
    print("✓ 正常動作")

    # テストケース3: 空リスト
    print("\n[テスト2-3] 空リスト")
    result = detect_unregistered_stores([], mapping_data)
    print(f"未登録店舗リスト: {result}")
    assert len(result) == 0, "空リストを返すべき"
    print("✓ 正常動作")


def test_determine_categories_batch():
    """determine_categories_batch() のテスト"""
    print_section("Test 3: determine_categories_batch()")

    # マッピングデータを読み込み
    mapping_data = load_mapping_data('config/mapping.json')

    # テストケース1: 複数レコードの一括処理
    print("\n[テスト3-1] 複数レコードの一括処理")
    records = [
        {'date': '2025/08/15', 'store': 'ユシンヤ', 'amount': 5780},
        {'date': '2025/08/16', 'store': 'AMAZON', 'amount': 1200},
        {'date': '2025/08/17', 'store': '未登録店舗', 'amount': 3000},
    ]
    result = determine_categories_batch(records, mapping_data)
    print(f"入力レコード数: {len(records)}")
    print(f"出力レコード数: {len(result)}")

    assert len(result) == 3, "出力レコード数は入力と同じであるべき"

    # 1件目（ユシンヤ）
    assert result[0]['store'] == 'ユシンヤ', "1件目の店舗名が保持されているべき"
    assert result[0]['matched'] is True, "1件目はマッチしているべき"
    assert result[0]['category'] == '外食費', "1件目のカテゴリは外食費であるべき"
    assert result[0]['column'] == 'C', "1件目の列番号はCであるべき"
    print(f"  レコード1: {result[0]}")

    # 2件目（AMAZON）
    assert result[1]['store'] == 'AMAZON', "2件目の店舗名が保持されているべき"
    assert result[1]['matched'] is True, "2件目はマッチしているべき"
    print(f"  レコード2: {result[1]}")

    # 3件目（未登録店舗）
    assert result[2]['store'] == '未登録店舗', "3件目の店舗名が保持されているべき"
    assert result[2]['matched'] is False, "3件目はマッチしていないべき"
    assert result[2]['category'] == '支払額', "3件目のカテゴリはデフォルトであるべき"
    assert result[2]['column'] == 'B', "3件目の列番号はBであるべき"
    print(f"  レコード3: {result[2]}")
    print("✓ 正常動作")

    # テストケース2: storeフィールドがない場合
    print("\n[テスト3-2] storeフィールドがない場合")
    records = [
        {'date': '2025/08/15', 'amount': 5780},  # storeフィールドなし
    ]
    result = determine_categories_batch(records, mapping_data)
    print(f"結果: {result[0]}")
    assert result[0]['matched'] is False, "マッチしていないべき"
    assert result[0]['category'] == '支払額', "デフォルトカテゴリであるべき"
    assert result[0]['column'] == 'B', "デフォルト列であるべき"
    print("✓ 正常動作")


def main():
    """メイン処理"""
    print("\n" + "="*60)
    print("  Phase 4 実装テスト開始")
    print("="*60)

    try:
        test_determine_category()
        test_detect_unregistered_stores()
        test_determine_categories_batch()

        print("\n" + "="*60)
        print("  ✓ すべてのテストが成功しました")
        print("="*60 + "\n")
        return 0

    except AssertionError as e:
        print(f"\n✗ テスト失敗: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ エラー発生: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
