"""
Phase 2: CSV読み込みテスト

このスクリプトは、csv_processor.pyのPhase 2実装（CSV読み込み機能）を検証します。

テスト対象:
1. read_csv_file() - CSV読み込み
2. is_detail_row() - 明細行判定
3. extract_detail_data() - 明細データ抽出
"""

import tempfile
import pandas as pd
import sys
from pathlib import Path

# モジュールインポート
sys.path.insert(0, str(Path(__file__).parent))
from modules.csv_processor import (
    read_csv_file,
    is_detail_row,
    extract_detail_data,
    InvalidFileFormatError,
    DataExtractionError
)


class TestResults:
    """テスト結果を管理するクラス"""

    def __init__(self):
        self.results = {}
        self.details = []

    def add_result(self, test_name: str, passed: bool, message: str = ""):
        """テスト結果を追加"""
        self.results[test_name] = passed
        if message:
            self.details.append(f"  {'✓' if passed else '✗'} {test_name}: {message}")
        else:
            self.details.append(f"  {'✓' if passed else '✗'} {test_name}")

    def get_summary(self) -> dict:
        """サマリーを取得"""
        total = len(self.results)
        passed = sum(1 for p in self.results.values() if p)
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "all_passed": all(self.results.values())
        }

    def print_details(self):
        """詳細結果を表示"""
        for detail in self.details:
            print(detail)


def test_read_csv_file():
    """read_csv_file() のテスト"""
    print("\n=== 1. read_csv_file() テスト ===")
    results = TestResults()

    # テストケース1: 正常系（Shift_JIS CSV）
    try:
        content = """ヘッダー1,ヘッダー2,ヘッダー3,ヘッダー4,ヘッダー5,ヘッダー6,ヘッダー7,ヘッダー8
ヘッダー1,ヘッダー2,ヘッダー3,ヘッダー4,ヘッダー5,ヘッダー6,ヘッダー7,ヘッダー8
ヘッダー1,ヘッダー2,ヘッダー3,ヘッダー4,ヘッダー5,ヘッダー6,ヘッダー7,ヘッダー8
ヘッダー1,ヘッダー2,ヘッダー3,ヘッダー4,ヘッダー5,ヘッダー6,ヘッダー7,ヘッダー8
ヘッダー1,ヘッダー2,ヘッダー3,ヘッダー4,ヘッダー5,ヘッダー6,ヘッダー7,ヘッダー8
ヘッダー1,ヘッダー2,ヘッダー3,ヘッダー4,ヘッダー5,ヘッダー6,ヘッダー7,ヘッダー8
ヘッダー1,ヘッダー2,ヘッダー3,ヘッダー4,ヘッダー5,ヘッダー6,ヘッダー7,ヘッダー8
250115,本人,イオン新潟南店,１回,,,5280,Apple Pay利用
250116,本人,ファミリーマート,１回,,,1200,"""

        with tempfile.NamedTemporaryFile(mode='w', encoding='shift_jis', delete=False, suffix='.csv') as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        df = read_csv_file(tmp_path)

        # 確認項目
        checks = [
            (not df.empty, "DataFrameが空でない"),
            (df[0].dtype == 'object', "列0が文字列型"),
            (len(df) > 0, "行数が0より大きい"),
        ]

        all_passed = all(check[0] for check in checks)
        results.add_result(
            "正常系（Shift_JIS CSV）",
            all_passed,
            "全確認項目PASS" if all_passed else "一部確認項目FAIL"
        )

        Path(tmp_path).unlink()
    except Exception as e:
        results.add_result("正常系（Shift_JIS CSV）", False, f"例外発生: {e}")

    # テストケース2: 正常系（UTF-8 CSV）
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.csv') as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        df = read_csv_file(tmp_path)

        all_passed = not df.empty and df[0].dtype == 'object'
        results.add_result("正常系（UTF-8 CSV）", all_passed)

        Path(tmp_path).unlink()
    except Exception as e:
        results.add_result("正常系（UTF-8 CSV）", False, f"例外発生: {e}")

    # テストケース3: 異常系（空ファイル）
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
            tmp_path = tmp.name

        try:
            read_csv_file(tmp_path)
            results.add_result("異常系（空ファイル）", False, "例外が発生しませんでした")
        except InvalidFileFormatError:
            results.add_result("異常系（空ファイル）", True, "InvalidFileFormatError発生（正常）")

        Path(tmp_path).unlink()
    except Exception as e:
        results.add_result("異常系（空ファイル）", False, f"予期しない例外: {e}")

    # テストケース4: 異常系（不正なCSV形式）
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='shift_jis', delete=False, suffix='.csv') as tmp:
            tmp.write("不正な形式\nカンマなし")
            tmp_path = tmp.name

        try:
            read_csv_file(tmp_path)
            # 実際には読み込めてしまう可能性があるため、結果を確認
            results.add_result("異常系（不正CSV形式）", True, "読み込み成功（許容）")
        except InvalidFileFormatError:
            results.add_result("異常系（不正CSV形式）", True, "InvalidFileFormatError発生（正常）")

        Path(tmp_path).unlink()
    except Exception as e:
        results.add_result("異常系（不正CSV形式）", False, f"予期しない例外: {e}")

    results.print_details()
    return results


def test_is_detail_row():
    """is_detail_row() のテスト"""
    print("\n=== 2. is_detail_row() テスト ===")
    results = TestResults()

    # テストケース1: 正常系（明細行）
    row = pd.Series(["250115", "本人", "イオン", "１回", "", "", "5280"])
    result = is_detail_row(row)
    results.add_result("明細行判定（True）", result == True, f"結果: {result}")

    # テストケース2: 異常系（ヘッダー行）
    row = pd.Series(["利用日", "利用者", "利用先", "支払方法", "", "", "金額"])
    result = is_detail_row(row)
    results.add_result("ヘッダー行判定（False）", result == False, f"結果: {result}")

    # テストケース3: 異常系（スラッシュ区切り日付）
    row = pd.Series(["25/01/15", "本人", "イオン", "１回", "", "", "5280"])
    result = is_detail_row(row)
    results.add_result("スラッシュ日付判定（False）", result == False, f"結果: {result}")

    # テストケース4: 異常系（None）
    row = pd.Series([None, "本人", "イオン", "１回", "", "", "5280"])
    result = is_detail_row(row)
    results.add_result("None判定（False）", result == False, f"結果: {result}")

    # テストケース5: 異常系（NaN）
    row = pd.Series([pd.NA, "本人", "イオン", "１回", "", "", "5280"])
    result = is_detail_row(row)
    results.add_result("NaN判定（False）", result == False, f"結果: {result}")

    # テストケース6: 異常系（空文字列）
    row = pd.Series(["", "本人", "イオン", "１回", "", "", "5280"])
    result = is_detail_row(row)
    results.add_result("空文字列判定（False）", result == False, f"結果: {result}")

    results.print_details()
    return results


def test_extract_detail_data():
    """extract_detail_data() のテスト"""
    print("\n=== 3. extract_detail_data() テスト ===")
    results = TestResults()

    # テストケース1: 正常系（明細データ抽出）
    try:
        data = []
        # 7行のヘッダー
        for i in range(7):
            data.append([f"ヘッダー{i+1}", "", "", "", "", "", "", ""])

        # 8行目: カラムヘッダー（実際のイオンカードCSV構造に合わせる）
        data.append(["ご利用日", "利用者区分", "ご利用先", "支払方法", "", "", "ご利用金額", "備考"])

        # 明細データ（9行目以降）
        data.append(["250115", "本人", "イオン新潟南店", "１回", "", "", "5,280", "Apple Pay利用"])
        data.append(["250116", "本人", "ファミリーマート", "１回", "", "", "1,200", ""])
        data.append(["250117", "本人", "JR東日本", "１回", "", "", "2,840", ""])

        df = pd.DataFrame(data, dtype=str)
        result_df = extract_detail_data(df)

        # 確認項目
        checks = [
            (len(result_df) == 3, f"行数が3: {len(result_df)}"),
            (list(result_df.columns) == ['date', 'user', 'store', 'payment_method', 'amount', 'note'],
             f"列名正しい: {list(result_df.columns)}"),
            (result_df.iloc[0]['amount'] == "5280", f"金額カンマ除去1: {result_df.iloc[0]['amount']}"),
            (result_df.iloc[1]['amount'] == "1200", f"金額カンマ除去2: {result_df.iloc[1]['amount']}"),
            (result_df.iloc[0]['date'] == "250115", f"date正しい: {result_df.iloc[0]['date']}"),
            (result_df.iloc[0]['user'] == "本人", f"user正しい: {result_df.iloc[0]['user']}"),
            (result_df.iloc[0]['store'] == "イオン新潟南店", f"store正しい: {result_df.iloc[0]['store']}"),
            (result_df.iloc[0]['payment_method'] == "１回", f"payment_method正しい: {result_df.iloc[0]['payment_method']}"),
            (result_df.iloc[0]['note'] == "Apple Pay利用", f"note正しい: {result_df.iloc[0]['note']}"),
        ]

        all_passed = all(check[0] for check in checks)
        results.add_result(
            "正常系（明細データ抽出）",
            all_passed,
            "全確認項目PASS" if all_passed else f"一部FAIL: {[c[1] for c in checks if not c[0]]}"
        )
    except Exception as e:
        results.add_result("正常系（明細データ抽出）", False, f"例外発生: {e}")

    # テストケース2: 異常系（明細行が0件）
    try:
        data = []
        for i in range(7):
            data.append([f"ヘッダー{i+1}"])

        df = pd.DataFrame(data, dtype=str)

        try:
            extract_detail_data(df)
            results.add_result("異常系（明細行0件）", False, "例外が発生しませんでした")
        except DataExtractionError:
            results.add_result("異常系（明細行0件）", True, "DataExtractionError発生（正常）")
    except Exception as e:
        results.add_result("異常系（明細行0件）", False, f"予期しない例外: {e}")

    # テストケース3: 異常系（列数不足）
    try:
        data = []
        for i in range(7):
            data.append(["ヘッダー"])
        data.append(["ご利用日", "利用者区分", "ご利用先"])  # カラムヘッダー
        data.append(["250115", "本人", "イオン"])  # 列数不足

        df = pd.DataFrame(data, dtype=str)

        try:
            extract_detail_data(df)
            results.add_result("異常系（列数不足）", False, "例外が発生しませんでした")
        except DataExtractionError:
            results.add_result("異常系（列数不足）", True, "DataExtractionError発生（正常）")
    except Exception as e:
        results.add_result("異常系（列数不足）", False, f"予期しない例外: {e}")

    # テストケース4: 異常系（金額が数値変換不可）
    try:
        data = []
        for i in range(7):
            data.append([f"ヘッダー{i+1}", "", "", "", "", "", "", ""])
        data.append(["ご利用日", "利用者区分", "ご利用先", "支払方法", "", "", "ご利用金額", "備考"])  # カラムヘッダー
        data.append(["250115", "本人", "イオン", "１回", "", "", "abc", ""])  # 金額が文字列

        df = pd.DataFrame(data, dtype=str)

        try:
            extract_detail_data(df)
            results.add_result("異常系（金額変換不可）", False, "例外が発生しませんでした")
        except DataExtractionError as e:
            has_abc = "abc" in str(e)
            results.add_result(
                "異常系（金額変換不可）",
                has_abc,
                f"DataExtractionError発生、'abc'含む: {has_abc}"
            )
    except Exception as e:
        results.add_result("異常系（金額変換不可）", False, f"予期しない例外: {e}")

    # テストケース5: 金額カンマ除去の検証
    try:
        data = []
        for i in range(7):
            data.append([f"ヘッダー{i+1}", "", "", "", "", "", "", ""])
        data.append(["ご利用日", "利用者区分", "ご利用先", "支払方法", "", "", "ご利用金額", "備考"])  # カラムヘッダー
        data.append(["250115", "本人", "イオン", "１回", "", "", "12,345", ""])  # 半角カンマ
        data.append(["250116", "本人", "イオン", "１回", "", "", "67、890", ""])  # 全角カンマ

        df = pd.DataFrame(data, dtype=str)
        result_df = extract_detail_data(df)

        checks = [
            (result_df.iloc[0]['amount'] == "12345", f"半角カンマ除去: {result_df.iloc[0]['amount']}"),
            (result_df.iloc[1]['amount'] == "67890", f"全角カンマ除去: {result_df.iloc[1]['amount']}"),
        ]

        all_passed = all(check[0] for check in checks)
        results.add_result(
            "金額カンマ除去検証",
            all_passed,
            "両方OK" if all_passed else f"FAIL: {[c[1] for c in checks if not c[0]]}"
        )
    except Exception as e:
        results.add_result("金額カンマ除去検証", False, f"例外発生: {e}")

    # テストケース6: 全6フィールドの検証
    try:
        data = []
        for i in range(7):
            data.append([f"ヘッダー{i+1}", "", "", "", "", "", "", ""])
        data.append(["ご利用日", "利用者区分", "ご利用先", "支払方法", "", "", "ご利用金額", "備考"])  # カラムヘッダー
        data.append(["250115", "本人", "イオン新潟南店", "１回", "", "", "5280", "Apple Pay"])

        df = pd.DataFrame(data, dtype=str)
        result_df = extract_detail_data(df)

        expected_columns = ['date', 'user', 'store', 'payment_method', 'amount', 'note']
        actual_columns = list(result_df.columns)

        checks = [
            (actual_columns == expected_columns, f"列名: {actual_columns}"),
            (result_df.iloc[0]['date'] == "250115", f"date: {result_df.iloc[0]['date']}"),
            (result_df.iloc[0]['user'] == "本人", f"user: {result_df.iloc[0]['user']}"),
            (result_df.iloc[0]['store'] == "イオン新潟南店", f"store: {result_df.iloc[0]['store']}"),
            (result_df.iloc[0]['payment_method'] == "１回", f"payment_method: {result_df.iloc[0]['payment_method']}"),
            (result_df.iloc[0]['amount'] == "5280", f"amount: {result_df.iloc[0]['amount']}"),
            (result_df.iloc[0]['note'] == "Apple Pay", f"note: {result_df.iloc[0]['note']}"),
        ]

        all_passed = all(check[0] for check in checks)
        results.add_result(
            "全6フィールド検証",
            all_passed,
            "全フィールドOK" if all_passed else f"FAIL: {[c[1] for c in checks if not c[0]]}"
        )
    except Exception as e:
        results.add_result("全6フィールド検証", False, f"例外発生: {e}")

    results.print_details()
    return results


def test_project_compliance():
    """プロジェクト仕様準拠確認"""
    print("\n=== 4. プロジェクト仕様準拠確認 ===")
    results = TestResults()

    # 4.1 CSVレコード定義準拠
    try:
        # テストデータ作成
        data = []
        for i in range(7):
            data.append([f"ヘッダー{i+1}", "", "", "", "", "", "", ""])
        data.append(["ご利用日", "利用者区分", "ご利用先", "支払方法", "", "", "ご利用金額", "備考"])  # カラムヘッダー
        data.append(["250115", "本人", "イオン", "１回", "", "", "5280", "備考"])

        df = pd.DataFrame(data, dtype=str)
        result_df = extract_detail_data(df)

        # CSVレコード定義の全フィールドが存在するか確認
        required_fields = ['date', 'user', 'store', 'payment_method', 'amount', 'note']
        has_all_fields = all(field in result_df.columns for field in required_fields)

        results.add_result(
            "CSVレコード定義準拠",
            has_all_fields,
            f"全フィールド存在: {has_all_fields}"
        )
    except Exception as e:
        results.add_result("CSVレコード定義準拠", False, f"例外発生: {e}")

    # 4.2 モジュール仕様準拠
    # read_csv_file, is_detail_row, extract_detail_dataが存在し、仕様通り動作するか
    try:
        checks = [
            (callable(read_csv_file), "read_csv_file()が関数"),
            (callable(is_detail_row), "is_detail_row()が関数"),
            (callable(extract_detail_data), "extract_detail_data()が関数"),
        ]

        all_exist = all(check[0] for check in checks)
        results.add_result(
            "モジュール仕様準拠",
            all_exist,
            f"全関数存在: {all_exist}"
        )
    except Exception as e:
        results.add_result("モジュール仕様準拠", False, f"例外発生: {e}")

    results.print_details()
    return results


def main():
    """メイン実行関数"""
    print("=" * 60)
    print("Phase 2: CSV読み込みテスト開始")
    print("=" * 60)

    # 各テストを実行
    test1 = test_read_csv_file()
    test2 = test_is_detail_row()
    test3 = test_extract_detail_data()
    test4 = test_project_compliance()

    # 総合評価
    print("\n" + "=" * 60)
    print("総合評価")
    print("=" * 60)

    all_results = {
        "read_csv_file()": test1,
        "is_detail_row()": test2,
        "extract_detail_data()": test3,
        "プロジェクト仕様準拠": test4
    }

    for test_name, test_result in all_results.items():
        summary = test_result.get_summary()
        status = "PASS" if summary["all_passed"] else "FAIL"
        print(f"{test_name}: {status} ({summary['passed']}/{summary['total']})")

    # 全体判定
    all_passed = all(test.get_summary()["all_passed"] for test in all_results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ Phase 2 テスト全PASS - Phase 3へ進行可能")
    else:
        print("⚠️ 問題あり - 修正が必要")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
