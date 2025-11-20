#!/usr/bin/env python3
"""
Phase 4: 統合処理関数のテスト

このスクリプトは、generate_preview()とprocess_csv_file()の動作を検証します。

テスト内容:
1. generate_preview() - プレビュー生成
   - 10件のデータ → 先頭5件を返す
   - 3件のデータ → 3件すべてを返す
   - 空リスト → 空リストを返す

2. process_csv_file() - CSV統合処理
   - テストCSVファイルの全体処理
   - 全フィールドの抽出確認
   - 日付変換・金額変換の確認
   - プレビュー・サマリーの生成確認
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.csv_processor import (
    generate_preview,
    process_csv_file,
    CSVProcessingError
)


def test_generate_preview():
    """generate_preview()のテスト"""
    print("=" * 70)
    print("テスト: generate_preview()")
    print("=" * 70)

    # テストデータ作成(10件)
    test_data_10 = [
        {
            'date': '2025/01/15',
            'year': 2025,
            'month': 1,
            'month_str': '2025年1月',
            'store': f'テストストア{i}',
            'amount': 1000 + i * 100,
            'user': '本人',
            'payment_method': '1回払い',
            'note': ''
        }
        for i in range(10)
    ]

    # テストケース1: 10件のデータ → 先頭5件
    print("\nテストケース1: 10件のデータ → 先頭5件を返す")
    preview_10 = generate_preview(test_data_10)
    print(f"  入力件数: {len(test_data_10)}")
    print(f"  出力件数: {len(preview_10)}")
    assert len(preview_10) == 5, f"期待値: 5件, 実際: {len(preview_10)}件"
    print("  ✓ 正常: 先頭5件が返されました")

    # テストケース2: 3件のデータ → 3件すべて
    print("\nテストケース2: 3件のデータ → 3件すべてを返す")
    test_data_3 = test_data_10[:3]
    preview_3 = generate_preview(test_data_3)
    print(f"  入力件数: {len(test_data_3)}")
    print(f"  出力件数: {len(preview_3)}")
    assert len(preview_3) == 3, f"期待値: 3件, 実際: {len(preview_3)}件"
    print("  ✓ 正常: 3件すべてが返されました")

    # テストケース3: 空リスト → 空リスト
    print("\nテストケース3: 空リスト → 空リストを返す")
    test_data_empty = []
    preview_empty = generate_preview(test_data_empty)
    print(f"  入力件数: {len(test_data_empty)}")
    print(f"  出力件数: {len(preview_empty)}")
    assert len(preview_empty) == 0, f"期待値: 0件, 実際: {len(preview_empty)}件"
    print("  ✓ 正常: 空リストが返されました")

    print("\n✓ generate_preview()のすべてのテストが成功しました\n")


def test_process_csv_file():
    """process_csv_file()のテスト"""
    print("=" * 70)
    print("テスト: process_csv_file()")
    print("=" * 70)

    # テストファイルパス
    test_file = project_root / "tests" / "test_data" / "sample_real_ioncard.csv"

    if not test_file.exists():
        print(f"\n警告: テストファイルが見つかりません: {test_file}")
        print("このテストをスキップします")
        return

    print(f"\nテストファイル: {test_file}")

    try:
        # CSV処理実行
        result = process_csv_file(
            str(test_file),
            allowed_dir=str(project_root / "tests" / "test_data")
        )

        # 結果の検証
        print("\n--- 処理結果 ---")
        print(f"総件数: {result['total_count']}")
        print(f"合計金額: ¥{result['summary']['total_amount']:,}")
        print(f"日付範囲: {result['summary']['date_range']['start']} ～ {result['summary']['date_range']['end']}")
        print(f"プレビュー件数: {len(result['preview'])}")
        print(f"詳細データ件数: {len(result['details'])}")

        # 基本検証
        assert result['total_count'] > 0, "総件数が0です"
        assert len(result['details']) == result['total_count'], "詳細データ件数が一致しません"
        assert len(result['preview']) <= 5, f"プレビュー件数が5を超えています: {len(result['preview'])}"
        assert result['summary']['total_amount'] > 0, "合計金額が0です"

        print("\n--- 先頭データの詳細 ---")
        if result['details']:
            first_record = result['details'][0]
            print(f"日付: {first_record['date']}")
            print(f"年: {first_record['year']}")
            print(f"月: {first_record['month']}")
            print(f"月表示: {first_record['month_str']}")
            print(f"店舗名: {first_record['store']}")
            print(f"金額: ¥{first_record['amount']:,}")
            print(f"利用者: {first_record['user']}")
            print(f"支払方法: {first_record['payment_method']}")
            print(f"備考: {first_record['note']}")

            # フィールドの型チェック
            assert isinstance(first_record['date'], str), "dateフィールドが文字列ではありません"
            assert isinstance(first_record['year'], int), "yearフィールドが整数ではありません"
            assert isinstance(first_record['month'], int), "monthフィールドが整数ではありません"
            assert isinstance(first_record['month_str'], str), "month_strフィールドが文字列ではありません"
            assert isinstance(first_record['amount'], int), "amountフィールドが整数ではありません"

            # 日付形式チェック(YYYY/MM/DD)
            assert '/' in first_record['date'], "日付がYYYY/MM/DD形式ではありません"
            date_parts = first_record['date'].split('/')
            assert len(date_parts) == 3, "日付が3つのパートに分かれていません"
            assert len(date_parts[0]) == 4, "年が4桁ではありません"
            assert len(date_parts[1]) == 2, "月が2桁ではありません"
            assert len(date_parts[2]) == 2, "日が2桁ではありません"

            print("\n✓ すべてのフィールドが正しい形式で返されました")

        print("\n--- プレビューデータ ---")
        for i, record in enumerate(result['preview'], 1):
            print(f"{i}. {record['date']} | {record['store']} | ¥{record['amount']:,}")

        print("\n✓ process_csv_file()のテストが成功しました")

    except CSVProcessingError as e:
        print(f"\n✗ CSV処理エラー: {e.message}")
        if e.details:
            print(f"  詳細: {e.details}")
        raise

    except Exception as e:
        print(f"\n✗ 予期しないエラー: {type(e).__name__}: {str(e)}")
        raise


def main():
    """メイン処理"""
    print("\n" + "=" * 70)
    print("Phase 4: 統合処理関数のテスト開始")
    print("=" * 70 + "\n")

    try:
        # テスト実行
        test_generate_preview()
        test_process_csv_file()

        print("\n" + "=" * 70)
        print("すべてのテストが成功しました！")
        print("=" * 70 + "\n")

        return 0

    except AssertionError as e:
        print(f"\n✗ アサーションエラー: {str(e)}")
        return 1

    except Exception as e:
        print(f"\n✗ テスト実行中にエラーが発生しました: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
