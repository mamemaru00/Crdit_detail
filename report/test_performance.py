#!/usr/bin/env python3
"""
Phase 5: パフォーマンステスト

csv_processor.pyのパフォーマンスをテストするスクリプト
- 1000件データの処理時間が30秒以内であることを確認
- 10MBファイルを正常に処理できることを確認
"""

import sys
import time
import tempfile
from pathlib import Path

# モジュールのインポート
sys.path.insert(0, str(Path(__file__).parent))
from modules.csv_processor import process_csv_file


def generate_csv_content_with_record_count(record_count: int) -> str:
    """指定件数のテストデータを含むCSV内容を生成

    Args:
        record_count (int): 生成する明細件数

    Returns:
        str: CSV内容(Shift_JIS用)
    """
    # ヘッダー部(7行) - カンマ区切りで列数を統一(8列)
    header_lines = [
        "イオンカード利用明細,,,,,,,",
        "会員番号,1234-5678-9012-3456,,,,,,",
        "利用期間,2025年1月,,,,,,",
        "ご請求金額,999999円,,,,,,",
        ",,,,,,,",
        "--- 明細データ ---,,,,,,,",
        "利用日,利用者,利用先,支払方法,回数,ポイント,利用金額,備考"
    ]

    # 明細データ生成(8行目以降)
    detail_lines = []
    for i in range(record_count):
        # 日付: 250101 ~ 250131をループ
        day = (i % 31) + 1
        date = f"2501{day:02d}"

        # 店舗名バリエーション
        stores = [
            "イオンスタイル幕張新都心",
            "セブンイレブン千葉店",
            "ローソン東京店",
            "ファミリーマート渋谷店",
            "スターバックス新宿店",
            "マクドナルド銀座店",
            "吉野家池袋店",
            "すき家上野店",
            "松屋浅草店",
            "ガスト品川店"
        ]
        store = stores[i % len(stores)]

        # 金額: 1000 ~ 10000円
        amount = (i % 10 + 1) * 1000

        detail_line = f"{date},本人,{store},1回払い,1,10,{amount},テストデータ{i+1}"
        detail_lines.append(detail_line)

    # すべての行を結合
    all_lines = header_lines + detail_lines
    return "\n".join(all_lines)


def generate_csv_file_with_size(target_size_mb: float, output_dir: str) -> str:
    """指定サイズのCSVファイルを生成

    Args:
        target_size_mb (float): 目標ファイルサイズ(MB)
        output_dir (str): 出力ディレクトリパス

    Returns:
        str: 生成されたファイルパス
    """
    target_size_bytes = int(target_size_mb * 1024 * 1024)

    # まず100件で試算
    test_content = generate_csv_content_with_record_count(100)
    bytes_per_100_records = len(test_content.encode('shift_jis'))

    # 必要な件数を計算
    estimated_records = int((target_size_bytes / bytes_per_100_records) * 100)

    # 少し多めに生成して調整
    content = generate_csv_content_with_record_count(estimated_records)
    content_bytes = content.encode('shift_jis')

    # サイズが目標未満なら追加
    while len(content_bytes) < target_size_bytes:
        # 100件追加
        additional_content = generate_csv_content_with_record_count(estimated_records + 100)
        content = additional_content
        content_bytes = content.encode('shift_jis')
        estimated_records += 100

    # 指定ディレクトリ内にファイルを作成
    csv_file = Path(output_dir) / f"test_{target_size_mb}mb.csv"
    csv_file.write_text(content, encoding='shift_jis')

    return str(csv_file)


def test_1000_records_within_30_seconds():
    """1000件のデータを30秒以内に処理できること"""
    print("\n【テスト1】1000件データ処理テスト")
    print("=" * 60)

    # 1000件のCSVファイル生成
    print("1000件のテストデータを生成中...")
    csv_content = generate_csv_content_with_record_count(1000)

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "test_1000_records.csv"
        csv_file.write_text(csv_content, encoding='shift_jis')

        file_size_mb = csv_file.stat().st_size / (1024 * 1024)
        print(f"ファイルサイズ: {file_size_mb:.2f}MB")
        print(f"明細件数: 1000件")

        # 処理時間計測
        print("\n処理開始...")
        start_time = time.time()

        try:
            result = process_csv_file(str(csv_file), tmpdir)

            elapsed_time = time.time() - start_time

            # 結果検証(±1件の誤差は許容)
            assert 999 <= result['total_count'] <= 1001, f"件数が想定範囲外です: {result['total_count']} (期待: 999-1001)"
            assert elapsed_time < 30, f"処理時間が30秒を超えました: {elapsed_time:.2f}秒"

            print(f"処理完了: {elapsed_time:.2f}秒")
            print(f"総件数: {result['total_count']}件")
            print(f"合計金額: {result['summary']['total_amount']:,}円")
            print(f"日付範囲: {result['summary']['date_range']['start']} ~ {result['summary']['date_range']['end']}")

            # パフォーマンス指標
            records_per_second = result['total_count'] / elapsed_time
            print(f"\nパフォーマンス指標:")
            print(f"  処理速度: {records_per_second:.2f}件/秒")
            print(f"  1件あたり処理時間: {elapsed_time * 1000 / result['total_count']:.2f}ms")

            print("\n✓ テスト成功: 1000件データを30秒以内に処理できました")
            return True

        except AssertionError as e:
            print(f"\n✗ テスト失敗: {str(e)}")
            return False
        except Exception as e:
            print(f"\n✗ テスト失敗(例外): {type(e).__name__}: {str(e)}")
            return False


def test_10mb_file_processing():
    """10MBのファイルを処理できること"""
    print("\n【テスト2】10MB大容量ファイル処理テスト")
    print("=" * 60)

    # 9.5MBのCSVファイル生成(10MB制限ギリギリなので少し小さめに)
    print("9.5MBのテストデータを生成中...")

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file_path = generate_csv_file_with_size(9.5, tmpdir)

        try:
            file_size_mb = Path(csv_file_path).stat().st_size / (1024 * 1024)
            print(f"ファイルサイズ: {file_size_mb:.2f}MB")

            # 処理時間計測
            print("\n処理開始...")
            start_time = time.time()

            result = process_csv_file(csv_file_path, tmpdir)

            elapsed_time = time.time() - start_time

            # 結果検証
            assert result['total_count'] > 0, "明細件数が0です"
            assert 'details' in result, "detailsキーが存在しません"
            assert 'preview' in result, "previewキーが存在しません"
            assert 'summary' in result, "summaryキーが存在しません"

            print(f"処理完了: {elapsed_time:.2f}秒")
            print(f"総件数: {result['total_count']}件")
            print(f"合計金額: {result['summary']['total_amount']:,}円")
            print(f"日付範囲: {result['summary']['date_range']['start']} ~ {result['summary']['date_range']['end']}")

            # パフォーマンス指標
            mb_per_second = file_size_mb / elapsed_time
            records_per_second = result['total_count'] / elapsed_time
            print(f"\nパフォーマンス指標:")
            print(f"  処理速度: {mb_per_second:.2f}MB/秒")
            print(f"  処理速度: {records_per_second:.2f}件/秒")
            print(f"  1件あたり処理時間: {elapsed_time * 1000 / result['total_count']:.2f}ms")

            print("\n✓ テスト成功: 10MBファイルを正常に処理できました")
            return True

        except AssertionError as e:
            print(f"\n✗ テスト失敗: {str(e)}")
            return False
        except Exception as e:
            print(f"\n✗ テスト失敗(例外): {type(e).__name__}: {str(e)}")
            return False


def test_10mb_plus_file_rejection():
    """10MB超過ファイルがエラーになることを確認"""
    print("\n【テスト3】10MB超過ファイル拒否テスト")
    print("=" * 60)

    # 11MBのCSVファイル生成
    print("11MBのテストデータを生成中...")

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file_path = generate_csv_file_with_size(11.0, tmpdir)

        try:
            file_size_mb = Path(csv_file_path).stat().st_size / (1024 * 1024)
            print(f"ファイルサイズ: {file_size_mb:.2f}MB")

            # 処理実行(エラーが発生することを期待)
            print("\n処理開始...")

            try:
                result = process_csv_file(csv_file_path, tmpdir)
                print("\n✗ テスト失敗: 10MB超過ファイルが拒否されませんでした")
                return False
            except Exception as e:
                # InvalidFileFormatErrorが発生することを期待
                error_message = str(e)
                if "制限を超えています" in error_message or "10" in error_message:
                    print(f"エラー発生(期待通り): {error_message}")
                    print("\n✓ テスト成功: 10MB超過ファイルが正しく拒否されました")
                    return True
                else:
                    print(f"\n✗ テスト失敗: 予期しないエラー: {type(e).__name__}: {error_message}")
                    return False

        except Exception as e:
            print(f"\n✗ テスト失敗(例外): {type(e).__name__}: {str(e)}")
            return False


def main():
    """メインテスト実行関数"""
    print("\n" + "=" * 60)
    print("Phase 5: パフォーマンステスト実行")
    print("=" * 60)

    results = []

    # テスト1: 1000件データ処理テスト
    results.append(("1000件データ処理(30秒以内)", test_1000_records_within_30_seconds()))

    # テスト2: 10MBファイル処理テスト
    results.append(("10MB大容量ファイル処理", test_10mb_file_processing()))

    # テスト3: 10MB超過ファイル拒否テスト
    results.append(("10MB超過ファイル拒否", test_10mb_plus_file_rejection()))

    # サマリー表示
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0
    print(f"\n合計: {passed_count}/{total_count} PASS ({pass_rate:.1f}%)")

    if passed_count == total_count:
        print("\n全テストが成功しました!")
        return 0
    else:
        print(f"\n{total_count - passed_count}件のテストが失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
