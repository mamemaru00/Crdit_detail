#!/usr/bin/env python3
"""
csv_processor.pyの正常系テスト(pytest形式)

カバレッジ向上のための正常系テストケース
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
    generate_preview,
    validate_file_path,
    validate_file_size,
    detect_encoding,
    is_detail_row
)
import pandas as pd


# ==================== 正常系テスト ====================

def test_process_csv_file_normal():
    """CSV全体処理が正常に動作すること"""
    csv_content = """イオンカード利用明細,,,,,,,
会員番号,1234-5678-9012-3456,,,,,,
利用期間,2025年1月,,,,,,
ご請求金額,10000円,,,,,,
,,,,,,,
--- 明細データ ---,,,,,,,
利用日,利用者,利用先,支払方法,回数,ポイント,利用金額,備考
250115,本人,イオンスタイル幕張新都心,1回払い,1,52,5280,テスト1
250116,本人,セブンイレブン千葉店,1回払い,1,12,1200,テスト2
250117,本人,ローソン東京店,1回払い,1,35,3520,テスト3"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "normal.csv"
        csv_file.write_text(csv_content, encoding='shift_jis')

        result = process_csv_file(str(csv_file), tmpdir)

        assert result['total_count'] == 3
        assert len(result['details']) == 3
        assert len(result['preview']) == 3
        assert result['summary']['total_amount'] == 10000
        assert result['details'][0]['date'] == '2025/01/15'
        assert result['details'][0]['year'] == 2025
        assert result['details'][0]['month'] == 1
        assert result['details'][0]['month_str'] == '2025年1月'


def test_read_csv_file_normal():
    """CSV読み込みが正常に動作すること"""
    csv_content = """イオンカード,利用明細
会員番号,1234-5678-9012-3456
利用日,店舗名,金額
250115,イオン,5280"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "normal.csv"
        csv_file.write_text(csv_content, encoding='shift_jis')

        df = read_csv_file(str(csv_file))

        assert not df.empty
        assert len(df) == 4


def test_extract_detail_data_normal():
    """明細データ抽出が正常に動作すること"""
    data = {
        0: ['ヘッダー1', 'ヘッダー2', 'ヘッダー3', 'ヘッダー4', 'ヘッダー5', 'ヘッダー6', 'ヘッダー7',
            '250115', '250116'],
        1: ['本人', '本人', '本人', '本人', '本人', '本人', '本人', '本人', '本人'],
        2: ['店舗1', '店舗2', '店舗3', '店舗4', '店舗5', '店舗6', '店舗7', 'イオン', 'セブンイレブン'],
        3: ['1回', '1回', '1回', '1回', '1回', '1回', '1回', '1回払い', '1回払い'],
        4: ['1', '1', '1', '1', '1', '1', '1', '1', '1'],
        5: ['0', '0', '0', '0', '0', '0', '0', '52', '12'],
        6: ['0', '0', '0', '0', '0', '0', '0', '5280', '1200'],
        7: ['', '', '', '', '', '', '', 'テスト1', 'テスト2']
    }
    df = pd.DataFrame(data)

    detail_df = extract_detail_data(df)

    assert len(detail_df) == 2
    assert 'date' in detail_df.columns
    assert 'store' in detail_df.columns
    assert 'amount' in detail_df.columns
    assert detail_df.iloc[0]['store'] == 'イオン'


def test_convert_date_format_normal():
    """日付変換が正常に動作すること"""
    assert convert_date_format("250115") == "2025/01/15"
    assert convert_date_format("241231") == "2024/12/31"
    assert convert_date_format("000101") == "2000/01/01"
    assert convert_date_format("491231") == "2049/12/31"
    assert convert_date_format("500101") == "1950/01/01"
    assert convert_date_format("991231") == "1999/12/31"


def test_extract_month_number_normal():
    """月番号抽出が正常に動作すること"""
    assert extract_month_number("250115") == 1
    assert extract_month_number("250601") == 6
    assert extract_month_number("251231") == 12


def test_generate_preview_normal():
    """プレビュー生成が正常に動作すること"""
    detail_data = [
        {'date': '2025/01/15', 'store': 'イオン', 'amount': 5280},
        {'date': '2025/01/16', 'store': 'セブンイレブン', 'amount': 1200},
        {'date': '2025/01/17', 'store': 'ローソン', 'amount': 3520},
        {'date': '2025/01/18', 'store': 'ファミリーマート', 'amount': 2100},
        {'date': '2025/01/19', 'store': 'スターバックス', 'amount': 980},
        {'date': '2025/01/20', 'store': 'マクドナルド', 'amount': 750},
        {'date': '2025/01/21', 'store': '吉野家', 'amount': 500}
    ]

    preview = generate_preview(detail_data)

    assert len(preview) == 5
    assert preview[0]['store'] == 'イオン'
    assert preview[4]['store'] == 'スターバックス'


def test_generate_preview_less_than_5():
    """5件未満のデータでプレビュー生成が正常に動作すること"""
    detail_data = [
        {'date': '2025/01/15', 'store': 'イオン', 'amount': 5280},
        {'date': '2025/01/16', 'store': 'セブンイレブン', 'amount': 1200}
    ]

    preview = generate_preview(detail_data)

    assert len(preview) == 2


def test_generate_preview_empty():
    """空データでプレビュー生成が空リストを返すこと"""
    preview = generate_preview([])
    assert preview == []


def test_validate_file_path_normal():
    """ファイルパス検証が正常に動作すること"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.csv"
        test_file.write_text("test")

        result = validate_file_path(str(test_file), tmpdir)
        assert result is True


def test_validate_file_size_normal():
    """ファイルサイズ検証が正常に動作すること"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"x" * (5 * 1024 * 1024))  # 5MB
        tmp_path = tmp.name

    try:
        result = validate_file_size(tmp_path)
        assert result is True
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_detect_encoding_shift_jis():
    """Shift_JISエンコーディング検出が正常に動作すること"""
    content = "利用日,利用先,金額\n250115,イオン,5280"
    with tempfile.NamedTemporaryFile(mode='w', encoding='shift_jis', delete=False, suffix='.csv') as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        encoding = detect_encoding(tmp_path)
        assert encoding in ['shift_jis', 'cp932', 'shift-jis']
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_detect_encoding_utf8():
    """UTF-8エンコーディング検出が正常に動作すること"""
    content = "利用日,利用先,金額\n250115,イオン,5280"
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.csv') as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        encoding = detect_encoding(tmp_path)
        assert encoding == 'utf-8'
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_is_detail_row_valid():
    """6桁数字の行判定が正常に動作すること"""
    row = pd.Series(['250115', '本人', 'イオン'])
    assert is_detail_row(row) is True


def test_is_detail_row_with_spaces():
    """空白付き6桁数字の行判定が正常に動作すること"""
    row = pd.Series(['  250115  ', '本人', 'イオン'])
    assert is_detail_row(row) is True


def test_is_detail_row_invalid():
    """非6桁数字の行判定が正常に動作すること"""
    row = pd.Series(['利用日', '利用者', '利用先'])
    assert is_detail_row(row) is False


def test_is_detail_row_none():
    """None値の行判定が正常に動作すること"""
    row = pd.Series([None, '本人', 'イオン'])
    assert is_detail_row(row) is False


def test_is_detail_row_empty():
    """空文字列の行判定が正常に動作すること"""
    row = pd.Series(['', '本人', 'イオン'])
    assert is_detail_row(row) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
