#!/usr/bin/env python3
"""
Phase 5: 異常系・境界値テスト

csv_processor.pyの異常系・境界値をテストするスクリプト
- 境界値テスト(空ファイル、ヘッダーのみ、1件のみ、最大サイズ)
- 異常データテスト(不正な日付、不正な金額、必須フィールド欠損、特殊文字)
- エンコーディングテスト(UTF-8、CP932、不正なエンコーディング)
"""

import sys
import tempfile
from pathlib import Path
import pytest

# モジュールのインポート
sys.path.insert(0, str(Path(__file__).parent))
from modules.csv_processor import (
    process_csv_file,
    read_csv_file,
    extract_detail_data,
    convert_date_format,
    extract_month_number,
    is_detail_row,
    CSVProcessingError,
    InvalidFileFormatError,
    DateConversionError,
    DataExtractionError,
    EncodingDetectionError
)
import pandas as pd


# ==================== 境界値テスト ====================

def test_empty_csv_file():
    """空のCSVファイルを処理するとエラーが発生すること"""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "empty.csv"
        csv_file.write_text("", encoding='shift_jis')

        with pytest.raises(InvalidFileFormatError) as exc_info:
            process_csv_file(str(csv_file), tmpdir)

        assert "空です" in str(exc_info.value)


def test_header_only_csv_file():
    """ヘッダーのみのCSVファイル(明細データなし)を処理するとエラーが発生すること"""
    header_only_content = """イオンカード,利用明細
会員番号,1234-5678-9012-3456
利用期間,2025年1月
ご請求金額,12345円
,
--- 明細データ ---
利用日,利用者,利用先,支払方法,回数,ポイント,利用金額,備考"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "header_only.csv"
        csv_file.write_text(header_only_content, encoding='shift_jis')

        with pytest.raises(DataExtractionError) as exc_info:
            process_csv_file(str(csv_file), tmpdir)

        assert "明細行が見つかりませんでした" in str(exc_info.value)


def test_single_record_csv_file():
    """1件のみの明細データを正常に処理できること"""
    single_record_content = """イオンカード,利用明細
会員番号,1234-5678-9012-3456
利用期間,2025年1月
ご請求金額,5280円
,
--- 明細データ ---
利用日,利用者,利用先,支払方法,回数,ポイント,利用金額,備考
250115,本人,イオンスタイル幕張新都心,1回払い,1,52,5280,テスト"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "single_record.csv"
        csv_file.write_text(single_record_content, encoding='shift_jis')

        result = process_csv_file(str(csv_file), tmpdir)

        assert result['total_count'] == 1
        assert len(result['details']) == 1
        assert result['details'][0]['date'] == '2025/01/15'
        assert result['details'][0]['store'] == 'イオンスタイル幕張新都心'
        assert result['details'][0]['amount'] == 5280


def test_exactly_10mb_file():
    """ちょうど10MBのファイルを正常に処理できること"""
    # 1行あたりのバイト数を計算
    test_line = "250115,本人,イオンスタイル幕張新都心,1回払い,1,52,5280,テストデータ\n"
    bytes_per_line = len(test_line.encode('shift_jis'))

    # ヘッダー部
    header_content = """イオンカード,利用明細
会員番号,1234-5678-9012-3456
利用期間,2025年1月
ご請求金額,999999円
,
--- 明細データ ---
利用日,利用者,利用先,支払方法,回数,ポイント,利用金額,備考
"""

    header_bytes = len(header_content.encode('shift_jis'))

    # 10MB = 10 * 1024 * 1024 バイト
    target_size = 10 * 1024 * 1024
    remaining_bytes = target_size - header_bytes

    # 必要な行数を計算(少し少なめに)
    num_records = int(remaining_bytes / bytes_per_line) - 1

    # データ行生成
    detail_lines = []
    for i in range(num_records):
        day = (i % 31) + 1
        date = f"2501{day:02d}"
        detail_line = f"{date},本人,イオンスタイル幕張新都心,1回払い,1,52,5280,テストデータ{i+1}"
        detail_lines.append(detail_line)

    full_content = header_content + "\n".join(detail_lines)

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "exactly_10mb.csv"
        csv_file.write_text(full_content, encoding='shift_jis')

        file_size = csv_file.stat().st_size

        # ファイルサイズが10MB以下であることを確認
        assert file_size <= 10 * 1024 * 1024, f"ファイルサイズが10MBを超えています: {file_size / (1024 * 1024):.2f}MB"

        # 処理実行
        result = process_csv_file(str(csv_file), tmpdir)

        # 正常に処理できたことを確認
        assert result['total_count'] > 0
        assert len(result['details']) == result['total_count']


# ==================== 異常データテスト ====================

def test_invalid_date_5_digits():
    """5桁の日付でエラーが発生すること"""
    with pytest.raises(DateConversionError) as exc_info:
        convert_date_format("25011")  # 5桁

    assert "6桁の数字である必要があります" in str(exc_info.value)


def test_invalid_date_7_digits():
    """7桁の日付でエラーが発生すること"""
    with pytest.raises(DateConversionError) as exc_info:
        convert_date_format("2501151")  # 7桁

    assert "6桁の数字である必要があります" in str(exc_info.value)


def test_invalid_date_with_letters():
    """文字列を含む日付でエラーが発生すること"""
    with pytest.raises(DateConversionError) as exc_info:
        convert_date_format("25011A")  # 文字列含む

    assert "6桁の数字である必要があります" in str(exc_info.value)


def test_invalid_month_00():
    """月が00の日付でエラーが発生すること"""
    with pytest.raises(DateConversionError) as exc_info:
        convert_date_format("250015")  # 月00

    assert "1-12の範囲である必要があります" in str(exc_info.value)


def test_invalid_month_13():
    """月が13の日付でエラーが発生すること"""
    with pytest.raises(DateConversionError) as exc_info:
        convert_date_format("251301")  # 月13

    assert "1-12の範囲である必要があります" in str(exc_info.value)


def test_invalid_day_00():
    """日が00の日付でエラーが発生すること"""
    with pytest.raises(DateConversionError) as exc_info:
        convert_date_format("250100")  # 日00

    assert "1-31の範囲である必要があります" in str(exc_info.value)


def test_invalid_day_32():
    """日が32の日付でエラーが発生すること"""
    with pytest.raises(DateConversionError) as exc_info:
        convert_date_format("250132")  # 日32

    assert "1-31の範囲である必要があります" in str(exc_info.value)


def test_invalid_amount_with_letters():
    """文字列を含む金額でエラーが発生すること"""
    csv_content = """イオンカード,利用明細
会員番号,1234-5678-9012-3456
利用期間,2025年1月
ご請求金額,ABC円
,
--- 明細データ ---
利用日,利用者,利用先,支払方法,回数,ポイント,利用金額,備考
250115,本人,イオン,1回払い,1,52,ABC,テスト"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "invalid_amount.csv"
        csv_file.write_text(csv_content, encoding='shift_jis')

        with pytest.raises(DataExtractionError) as exc_info:
            process_csv_file(str(csv_file), tmpdir)

        assert "数値変換できない" in str(exc_info.value)


def test_missing_required_column():
    """必須列が不足しているCSVでエラーが発生すること"""
    # 列が4つしかないCSV(本来は7列以上必要)
    csv_content = """イオンカード,利用明細
会員番号,1234-5678-9012-3456
利用期間,2025年1月
ご請求金額,5280円
,
--- 明細データ ---
利用日,利用者,利用先,支払方法
250115,本人,イオン,1回払い"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "missing_columns.csv"
        csv_file.write_text(csv_content, encoding='shift_jis')

        with pytest.raises(DataExtractionError) as exc_info:
            process_csv_file(str(csv_file), tmpdir)

        assert "必要な列が存在しません" in str(exc_info.value)


def test_special_characters_in_store_name():
    """特殊文字を含む店舗名を正常に処理できること"""
    csv_content = """イオンカード,利用明細
会員番号,1234-5678-9012-3456
利用期間,2025年1月
ご請求金額,10000円
,
--- 明細データ ---
利用日,利用者,利用先,支払方法,回数,ポイント,利用金額,備考
250115,本人,髙島屋①号店&カフェ【特別】,1回払い,1,52,5280,テスト①
250116,本人,﨑陽軒②号店＜新店＞,1回払い,1,52,4720,テスト②"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "special_chars.csv"
        csv_file.write_text(csv_content, encoding='cp932')

        result = process_csv_file(str(csv_file), tmpdir)

        assert result['total_count'] == 2
        assert '髙島屋①号店&カフェ【特別】' in result['details'][0]['store']
        assert '﨑陽軒②号店＜新店＞' in result['details'][1]['store']


# ==================== エンコーディングテスト ====================

def test_utf8_encoded_csv():
    """UTF-8エンコーディングのCSVを正常に処理できること"""
    csv_content = """イオンカード,利用明細
会員番号,1234-5678-9012-3456
利用期間,2025年1月
ご請求金額,5280円
,
--- 明細データ ---
利用日,利用者,利用先,支払方法,回数,ポイント,利用金額,備考
250115,本人,イオンスタイル幕張新都心,1回払い,1,52,5280,テスト"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "utf8.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        result = process_csv_file(str(csv_file), tmpdir)

        assert result['total_count'] == 1
        assert result['details'][0]['store'] == 'イオンスタイル幕張新都心'


def test_cp932_encoded_csv_with_special_chars():
    """CP932エンコーディング(特殊文字含む)のCSVを正常に処理できること"""
    csv_content = """イオンカード,利用明細
会員番号,1234-5678-9012-3456
利用期間,2025年1月
ご請求金額,10000円
,
--- 明細データ ---
利用日,利用者,利用先,支払方法,回数,ポイント,利用金額,備考
250115,本人,髙島屋,1回払い,1,52,5280,テスト
250116,本人,﨑陽軒,1回払い,1,52,4720,テスト"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "cp932.csv"
        csv_file.write_text(csv_content, encoding='cp932')

        result = process_csv_file(str(csv_file), tmpdir)

        assert result['total_count'] == 2
        assert result['details'][0]['store'] == '髙島屋'
        assert result['details'][1]['store'] == '﨑陽軒'


def test_binary_file_encoding_detection_error():
    """バイナリファイルでエンコーディング検出エラーが発生すること"""
    with tempfile.TemporaryDirectory() as tmpdir:
        binary_file = Path(tmpdir) / "binary.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09')

        with pytest.raises((EncodingDetectionError, InvalidFileFormatError)):
            process_csv_file(str(binary_file), tmpdir)


# ==================== is_detail_row() 境界値テスト ====================

def test_is_detail_row_with_none():
    """None値を含む行でFalseを返すこと"""
    row = pd.Series([None, '本人', 'イオン'])
    assert is_detail_row(row) is False


def test_is_detail_row_with_empty_string():
    """空文字列を含む行でFalseを返すこと"""
    row = pd.Series(['', '本人', 'イオン'])
    assert is_detail_row(row) is False


def test_is_detail_row_with_spaces():
    """空白のみの行でFalseを返すこと"""
    row = pd.Series(['   ', '本人', 'イオン'])
    assert is_detail_row(row) is False


def test_is_detail_row_with_valid_date():
    """6桁数字の行でTrueを返すこと"""
    row = pd.Series(['250115', '本人', 'イオン'])
    assert is_detail_row(row) is True


def test_is_detail_row_with_date_and_spaces():
    """6桁数字の前後に空白がある行でTrueを返すこと"""
    row = pd.Series(['  250115  ', '本人', 'イオン'])
    assert is_detail_row(row) is True


# ==================== extract_month_number() 境界値テスト ====================

def test_extract_month_number_boundary_01():
    """1月を正しく抽出できること"""
    assert extract_month_number("250115") == 1


def test_extract_month_number_boundary_12():
    """12月を正しく抽出できること"""
    assert extract_month_number("251231") == 12


def test_extract_month_number_invalid_00():
    """月00でエラーが発生すること"""
    with pytest.raises(DateConversionError) as exc_info:
        extract_month_number("250015")

    assert "1-12の範囲である必要があります" in str(exc_info.value)


def test_extract_month_number_invalid_13():
    """月13でエラーが発生すること"""
    with pytest.raises(DateConversionError) as exc_info:
        extract_month_number("251301")

    assert "1-12の範囲である必要があります" in str(exc_info.value)


# ==================== メイン実行 ====================

if __name__ == "__main__":
    # pytestを使用して実行
    pytest.main([__file__, "-v", "--tb=short"])
