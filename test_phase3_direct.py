"""
Phase 3: 日付変換関数の直接テスト

modules/csv_processor.pyから日付変換関数のコードを直接コピーして
テストします（pandas依存を回避）。
"""

import re


# ==================== 定数定義 ====================
DATE_PATTERN = r'^\d{6}$'  # 6桁数字パターン(YYMMDD)


# ==================== カスタム例外クラス ====================
class CSVProcessingError(Exception):
    """CSV処理の基底例外クラス"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DateConversionError(CSVProcessingError):
    """日付変換エラー"""
    pass


# ==================== 日付変換関数 ====================
def convert_date_format(yymmdd_str: str) -> str:
    """YYMMDD形式をYYYY/MM/DD形式に変換"""
    # 6桁数字のパターンマッチ
    if not re.match(DATE_PATTERN, yymmdd_str):
        raise DateConversionError(
            f"日付は6桁の数字である必要があります: {yymmdd_str}",
            details={
                "input": yymmdd_str,
                "expected_pattern": "YYMMDD (6桁数字)"
            }
        )

    # YY, MM, DDを抽出
    yy = int(yymmdd_str[0:2])
    mm = int(yymmdd_str[2:4])
    dd = int(yymmdd_str[4:6])

    # 月の妥当性チェック(1-12)
    if mm < 1 or mm > 12:
        raise DateConversionError(
            f"月は1-12の範囲である必要があります: {mm}",
            details={
                "input": yymmdd_str,
                "extracted_month": mm
            }
        )

    # 日の妥当性チェック(1-31)
    if dd < 1 or dd > 31:
        raise DateConversionError(
            f"日は1-31の範囲である必要があります: {dd}",
            details={
                "input": yymmdd_str,
                "extracted_day": dd
            }
        )

    # 年の判定(00-49 → 2000年代, 50-99 → 1900年代)
    if yy <= 49:
        yyyy = 2000 + yy
    else:
        yyyy = 1900 + yy

    # YYYY/MM/DD形式に変換
    return f"{yyyy:04d}/{mm:02d}/{dd:02d}"


def extract_month_number(yymmdd_str: str) -> int:
    """YYMMDD形式から月番号(1-12)を抽出"""
    # 6桁数字のパターンマッチ
    if not re.match(DATE_PATTERN, yymmdd_str):
        raise DateConversionError(
            f"日付は6桁の数字である必要があります: {yymmdd_str}",
            details={
                "input": yymmdd_str,
                "expected_pattern": "YYMMDD (6桁数字)"
            }
        )

    # MMを抽出
    mm = int(yymmdd_str[2:4])

    # 月の妥当性チェック(1-12)
    if mm < 1 or mm > 12:
        raise DateConversionError(
            f"月は1-12の範囲である必要があります: {mm}",
            details={
                "input": yymmdd_str,
                "extracted_month": mm
            }
        )

    return mm


# ==================== テスト実行 ====================
def test_convert_date_format():
    """convert_date_format関数のテスト"""
    print("\n=== convert_date_format関数のテスト ===\n")

    test_cases = [
        # (入力, 期待される出力, 説明)
        ("250115", "2025/01/15", "正常系: 2025年1月15日"),
        ("240229", "2024/02/29", "正常系: 2024年2月29日(閏年)"),
        ("000101", "2000/01/01", "正常系: 2000年1月1日"),
        ("491231", "2049/12/31", "正常系: 2049年12月31日(2000年代の境界)"),
        ("500101", "1950/01/01", "正常系: 1950年1月1日(1900年代の開始)"),
        ("991231", "1999/12/31", "正常系: 1999年12月31日"),
    ]

    passed = 0
    failed = 0

    for input_val, expected, description in test_cases:
        try:
            result = convert_date_format(input_val)
            if result == expected:
                print(f"✓ {description}")
                print(f"  入力: {input_val} → 出力: {result}")
                passed += 1
            else:
                print(f"✗ {description}")
                print(f"  入力: {input_val}")
                print(f"  期待: {expected}")
                print(f"  実際: {result}")
                failed += 1
        except Exception as e:
            print(f"✗ {description}")
            print(f"  入力: {input_val}")
            print(f"  エラー: {e}")
            failed += 1
        print()

    # 異常系テスト
    error_cases = [
        ("25011", "異常系: 5桁の数字"),
        ("2501155", "異常系: 7桁の数字"),
        ("251301", "異常系: 月が13"),
        ("250001", "異常系: 月が0"),
        ("250132", "異常系: 日が32"),
        ("250100", "異常系: 日が0"),
        ("25AB01", "異常系: 非数字文字"),
        ("", "異常系: 空文字列"),
    ]

    for input_val, description in error_cases:
        try:
            result = convert_date_format(input_val)
            print(f"✗ {description}")
            print(f"  入力: {input_val}")
            print(f"  期待: DateConversionError")
            print(f"  実際: {result} (エラーが発生しませんでした)")
            failed += 1
        except DateConversionError as e:
            print(f"✓ {description}")
            print(f"  入力: {input_val} → 正しくエラーが発生: {e.message}")
            passed += 1
        except Exception as e:
            print(f"✗ {description}")
            print(f"  入力: {input_val}")
            print(f"  予期しないエラー: {e}")
            failed += 1
        print()

    print(f"\nconvert_date_format: {passed}件成功, {failed}件失敗\n")
    return passed, failed


def test_extract_month_number():
    """extract_month_number関数のテスト"""
    print("\n=== extract_month_number関数のテスト ===\n")

    test_cases = [
        # (入力, 期待される出力, 説明)
        ("250115", 1, "正常系: 1月"),
        ("241231", 12, "正常系: 12月"),
        ("250601", 6, "正常系: 6月"),
    ]

    passed = 0
    failed = 0

    for input_val, expected, description in test_cases:
        try:
            result = extract_month_number(input_val)
            if result == expected and isinstance(result, int):
                print(f"✓ {description}")
                print(f"  入力: {input_val} → 出力: {result} (型: {type(result).__name__})")
                passed += 1
            else:
                print(f"✗ {description}")
                print(f"  入力: {input_val}")
                print(f"  期待: {expected} (int)")
                print(f"  実際: {result} ({type(result).__name__})")
                failed += 1
        except Exception as e:
            print(f"✗ {description}")
            print(f"  入力: {input_val}")
            print(f"  エラー: {e}")
            failed += 1
        print()

    # 1-12月すべてのテスト
    print("正常系: 1-12月すべて")
    all_months_passed = True
    for month in range(1, 13):
        date_str = f"25{month:02d}15"
        try:
            result = extract_month_number(date_str)
            if result != month or not isinstance(result, int):
                print(f"  ✗ {month}月失敗: 入力={date_str}, 出力={result}")
                all_months_passed = False
                failed += 1
        except Exception as e:
            print(f"  ✗ {month}月エラー: {e}")
            all_months_passed = False
            failed += 1

    if all_months_passed:
        print(f"  ✓ 1-12月すべて正常に動作")
        passed += 1
    print()

    # 異常系テスト
    error_cases = [
        ("25011", "異常系: 5桁の数字"),
        ("251301", "異常系: 月が13"),
        ("250001", "異常系: 月が0"),
        ("25AB01", "異常系: 非数字文字"),
    ]

    for input_val, description in error_cases:
        try:
            result = extract_month_number(input_val)
            print(f"✗ {description}")
            print(f"  入力: {input_val}")
            print(f"  期待: DateConversionError")
            print(f"  実際: {result} (エラーが発生しませんでした)")
            failed += 1
        except DateConversionError as e:
            print(f"✓ {description}")
            print(f"  入力: {input_val} → 正しくエラーが発生: {e.message}")
            passed += 1
        except Exception as e:
            print(f"✗ {description}")
            print(f"  入力: {input_val}")
            print(f"  予期しないエラー: {e}")
            failed += 1
        print()

    print(f"\nextract_month_number: {passed}件成功, {failed}件失敗\n")
    return passed, failed


def main():
    """メインテスト実行"""
    print("=" * 60)
    print("Phase 3: 日付変換関数のテスト")
    print("=" * 60)

    # convert_date_format関数のテスト
    passed1, failed1 = test_convert_date_format()

    # extract_month_number関数のテスト
    passed2, failed2 = test_extract_month_number()

    # 結果サマリー
    print("=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    total_passed = passed1 + passed2
    total_failed = failed1 + failed2
    total_tests = total_passed + total_failed

    print(f"\n合計: {total_tests}件のテスト")
    print(f"成功: {total_passed}件")
    print(f"失敗: {total_failed}件")

    if total_failed == 0:
        print("\n✓ すべてのテストに成功しました！")
        return 0
    else:
        print(f"\n✗ {total_failed}件のテストが失敗しました")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)
