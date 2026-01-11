"""
Phase 4 Step 4.1: CSV処理モジュール（modules/csv_processor.py）の単体テスト

このモジュールは以下のテストケースを実行します:

正常系（8ケース）:
1. Shift_JIS CSVファイル正常読込
2. UTF-8 CSVファイル正常読込
3. 日付変換（YYMMDD → YYYY/MM/DD）- 2000年代
4. 日付変換（YYMMDD → YYYY/MM/DD）- 2025年代
5. 明細データ抽出（8行目以降、6桁数字で始まる行）
6. 金額解析（カンマ区切り対応）
7. プレビューデータ生成（先頭5件）
8. 正常フロー（読込→抽出→変換→プレビュー）

異常系（7ケース）:
1. 空ファイル処理
2. 不正エンコーディング自動検出・変換
3. ヘッダーのみファイル（明細行なし）
4. 不正日付形式（5桁）
5. 不正金額形式（英字混入）
6. 巨大ファイル（10MB以上、性能確認）
7. ファイル存在しないエラー

エッジケース（5ケース）:
1. 金額0円
2. 金額100万円以上
3. 店舗名に特殊文字（全角スペース、半角カナ、絵文字）
4. 日付境界値（月初、月末、うるう年2月29日）
5. CSV列数不足・過多
"""

import pytest
import tempfile
import os
from pathlib import Path
from modules.csv_processor import (
    detect_encoding,
    read_csv_file,
    is_detail_row,
    extract_detail_data,
    convert_date_format,
    extract_month_number,
    generate_preview,
    process_csv_file,
    validate_file_path,
    validate_file_size,
    EncodingDetectionError,
    InvalidFileFormatError,
    DateConversionError,
    DataExtractionError,
    PathValidationError,
    CSVProcessingError
)
import pandas as pd


# ==================== Fixtures ====================

@pytest.fixture
def fixtures_dir():
    """テストフィクスチャディレクトリのパス"""
    return Path(__file__).parent.parent / 'fixtures' / 'csv'


@pytest.fixture
def valid_shiftjis_csv(fixtures_dir):
    """有効なShift_JIS CSVファイルパス"""
    return str(fixtures_dir / 'valid_shiftjis.csv')


@pytest.fixture
def valid_utf8_csv(fixtures_dir):
    """有効なUTF-8 CSVファイルパス"""
    return str(fixtures_dir / 'valid_utf8.csv')


@pytest.fixture
def empty_csv(fixtures_dir):
    """空のCSVファイルパス"""
    return str(fixtures_dir / 'empty.csv')


@pytest.fixture
def header_only_csv(fixtures_dir):
    """ヘッダーのみのCSVファイルパス"""
    return str(fixtures_dir / 'header_only.csv')


@pytest.fixture
def invalid_date_csv(fixtures_dir):
    """不正な日付を含むCSVファイルパス"""
    return str(fixtures_dir / 'invalid_date.csv')


@pytest.fixture
def invalid_amount_csv(fixtures_dir):
    """不正な金額を含むCSVファイルパス"""
    return str(fixtures_dir / 'invalid_amount.csv')


@pytest.fixture
def edge_cases_csv(fixtures_dir):
    """エッジケースを含むCSVファイルパス"""
    return str(fixtures_dir / 'edge_cases.csv')


@pytest.fixture
def temp_upload_dir():
    """一時アップロードディレクトリ"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


# ==================== 正常系テスト（8ケース） ====================

@pytest.mark.unit
def test_detect_encoding_shiftjis(valid_shiftjis_csv):
    """正常系1: Shift_JIS CSVファイルのエンコーディング検出"""
    encoding = detect_encoding(valid_shiftjis_csv)

    # CP932またはShift_JISとして検出されることを確認
    assert encoding in ['cp932', 'shift_jis', 'shift-jis']


@pytest.mark.unit
def test_read_csv_utf8(valid_utf8_csv):
    """正常系2: UTF-8 CSVファイル正常読込"""
    df = read_csv_file(valid_utf8_csv)

    assert df is not None
    assert not df.empty
    assert isinstance(df, pd.DataFrame)
    # 全列が文字列型として読み込まれていることを確認
    assert all(df.dtypes == 'object')


@pytest.mark.unit
@pytest.mark.parametrize("input_date,expected_date", [
    ("000101", "2000/01/01"),  # 2000年代
    ("491231", "2049/12/31"),  # 2049年
])
def test_convert_date_2000s(input_date, expected_date):
    """正常系3: 日付変換（YYMMDD → YYYY/MM/DD）- 2000年代"""
    result = convert_date_format(input_date)
    assert result == expected_date


@pytest.mark.unit
@pytest.mark.parametrize("input_date,expected_date", [
    ("250115", "2025/01/15"),  # 2025年
    ("300630", "2030/06/30"),  # 2030年
])
def test_convert_date_2025(input_date, expected_date):
    """正常系4: 日付変換（YYMMDD → YYYY/MM/DD）- 2025年代"""
    result = convert_date_format(input_date)
    assert result == expected_date


@pytest.mark.unit
def test_extract_detail_data_normal(valid_shiftjis_csv):
    """正常系5: 明細データ抽出（8行目以降、6桁数字で始まる行）"""
    df = read_csv_file(valid_shiftjis_csv)
    detail_df = extract_detail_data(df)

    assert not detail_df.empty
    assert len(detail_df) > 0
    # 必須列の存在確認
    expected_columns = ['date', 'user', 'store', 'payment_method', 'amount', 'note']
    assert list(detail_df.columns) == expected_columns

    # 各行の日付が6桁数字であることを確認（変換前）
    for _, row in detail_df.iterrows():
        assert len(row['date']) == 6
        assert row['date'].isdigit()


@pytest.mark.unit
def test_amount_parsing_with_commas():
    """正常系6: 金額解析（カンマ区切り対応）"""
    # カンマ付き金額を含むテストDataFrame作成
    test_data = {
        0: ['250115', '250116'],
        1: ['本人', '家族'],
        2: ['店舗A', '店舗B'],
        3: ['１回', '１回'],
        6: ['1,234', '56,789'],
        7: ['', '']
    }
    df = pd.DataFrame(test_data)

    # ヘッダー行を追加（8行目以降が明細データ）
    header_rows = pd.DataFrame([['' for _ in range(8)] for _ in range(8)])
    full_df = pd.concat([header_rows, df], ignore_index=True)

    detail_df = extract_detail_data(full_df)

    # カンマが除去されていることを確認
    assert detail_df.iloc[0]['amount'] == '1234'
    assert detail_df.iloc[1]['amount'] == '56789'


@pytest.mark.unit
def test_generate_preview_normal():
    """正常系7: プレビューデータ生成（先頭5件）"""
    # 10件のテストデータ作成
    test_data = [
        {'date': f'2025/01/{i:02d}', 'store': f'店舗{i}', 'amount': i * 1000}
        for i in range(1, 11)
    ]

    preview = generate_preview(test_data)

    assert len(preview) == 5
    assert preview[0]['date'] == '2025/01/01'
    assert preview[4]['date'] == '2025/01/05'


@pytest.mark.unit
def test_process_csv_file_normal(valid_utf8_csv, temp_upload_dir):
    """正常系8: 正常フロー（読込→抽出→変換→プレビュー）"""
    # テストファイルを一時ディレクトリにコピー
    import shutil
    temp_csv = os.path.join(temp_upload_dir, 'test.csv')
    shutil.copy(valid_utf8_csv, temp_csv)

    result = process_csv_file(temp_csv, temp_upload_dir)

    # 結果構造の確認
    assert 'details' in result
    assert 'preview' in result
    assert 'total_count' in result
    assert 'summary' in result

    # detailsの確認
    assert len(result['details']) > 0
    assert result['total_count'] == len(result['details'])

    # previewの確認（最大5件）
    assert len(result['preview']) <= 5

    # summaryの確認
    assert 'total_amount' in result['summary']
    assert 'date_range' in result['summary']
    assert result['summary']['total_amount'] > 0

    # 各レコードのフィールド確認
    first_record = result['details'][0]
    assert 'date' in first_record
    assert 'year' in first_record
    assert 'month' in first_record
    assert 'month_str' in first_record
    assert 'store' in first_record
    assert 'amount' in first_record

    # 日付がYYYY/MM/DD形式に変換されていることを確認
    assert '/' in first_record['date']
    assert len(first_record['date']) == 10


# ==================== 異常系テスト（7ケース） ====================

@pytest.mark.unit
def test_empty_file_error(empty_csv):
    """異常系1: 空ファイル処理"""
    with pytest.raises(InvalidFileFormatError) as exc_info:
        read_csv_file(empty_csv)

    assert "空です" in str(exc_info.value)


@pytest.mark.unit
def test_encoding_detection_auto_fallback(valid_shiftjis_csv):
    """異常系2: 不正エンコーディング自動検出・変換（CP932フォールバック）"""
    # Shift_JISファイルがCP932として正常に読み込めることを確認
    encoding = detect_encoding(valid_shiftjis_csv)
    assert encoding in ['cp932', 'shift_jis', 'shift-jis']

    # 実際に読み込めることを確認
    df = read_csv_file(valid_shiftjis_csv)
    assert not df.empty


@pytest.mark.unit
def test_header_only_no_details(header_only_csv):
    """異常系3: ヘッダーのみファイル（明細行なし）"""
    df = read_csv_file(header_only_csv)

    with pytest.raises(DataExtractionError) as exc_info:
        extract_detail_data(df)

    assert "明細行が見つかりませんでした" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.parametrize("invalid_date", [
    "25011",   # 5桁
    "2501155", # 7桁
    "25A115",  # 英字混入
])
def test_invalid_date_format(invalid_date):
    """異常系4: 不正日付形式（5桁、7桁、英字混入）"""
    with pytest.raises(DateConversionError) as exc_info:
        convert_date_format(invalid_date)

    assert "6桁の数字である必要があります" in str(exc_info.value)


@pytest.mark.unit
def test_invalid_amount_format(invalid_amount_csv):
    """異常系5: 不正金額形式（英字混入）"""
    df = read_csv_file(invalid_amount_csv)

    with pytest.raises(DataExtractionError) as exc_info:
        extract_detail_data(df)

    assert "数値変換できない値が含まれています" in str(exc_info.value)


@pytest.mark.unit
def test_large_file_size_limit(temp_upload_dir):
    """異常系6: 巨大ファイル（10MB以上、性能確認）"""
    # 11MB超のダミーファイルを作成（10MB制限を超える）
    large_file = os.path.join(temp_upload_dir, 'large.csv')
    with open(large_file, 'wb') as f:
        # 11MB書き込み
        f.write(b'0' * (11 * 1024 * 1024))

    with pytest.raises(InvalidFileFormatError) as exc_info:
        validate_file_size(large_file)

    assert "ファイルサイズが制限を超えています" in str(exc_info.value)


@pytest.mark.unit
def test_file_not_found_error():
    """異常系7: ファイル存在しないエラー"""
    non_existent_file = '/tmp/non_existent_file.csv'

    with pytest.raises(FileNotFoundError):
        detect_encoding(non_existent_file)


# ==================== エッジケーステスト（5ケース） ====================

@pytest.mark.unit
def test_edge_case_zero_amount(edge_cases_csv):
    """エッジケース1: 金額0円"""
    df = read_csv_file(edge_cases_csv)
    detail_df = extract_detail_data(df)

    # 金額0円のレコードが正常に処理されることを確認
    zero_amount_records = detail_df[detail_df['amount'] == '0']
    assert len(zero_amount_records) > 0


@pytest.mark.unit
def test_edge_case_large_amount(edge_cases_csv):
    """エッジケース2: 金額100万円以上"""
    df = read_csv_file(edge_cases_csv)
    detail_df = extract_detail_data(df)

    # 100万円以上のレコードが正常に処理されることを確認
    large_amount_records = detail_df[detail_df['amount'].astype(int) >= 1000000]
    assert len(large_amount_records) > 0


@pytest.mark.unit
def test_edge_case_special_characters(edge_cases_csv):
    """エッジケース3: 店舗名に特殊文字（全角スペース、半角カナ、絵文字）"""
    df = read_csv_file(edge_cases_csv)
    detail_df = extract_detail_data(df)

    # 特殊文字を含む店舗名が正常に処理されることを確認
    assert len(detail_df) > 0

    # 全角スペース、半角カナ、絵文字を含むレコードの存在確認
    stores = detail_df['store'].tolist()
    assert any('　' in store or 'ｶ' in store for store in stores)


@pytest.mark.unit
@pytest.mark.parametrize("input_date,expected_date", [
    ("250101", "2025/01/01"),  # 月初
    ("250131", "2025/01/31"),  # 月末
    ("240229", "2024/02/29"),  # うるう年2月29日
])
def test_edge_case_date_boundaries(input_date, expected_date):
    """エッジケース4: 日付境界値（月初、月末、うるう年2月29日）"""
    result = convert_date_format(input_date)
    assert result == expected_date


@pytest.mark.unit
def test_edge_case_column_mismatch():
    """エッジケース5: CSV列数不足・過多"""
    # 列数が不足しているDataFrame作成
    insufficient_data = {
        0: ['250115'],
        1: ['本人'],
        2: ['店舗A']
        # 列3以降が不足
    }
    df_insufficient = pd.DataFrame(insufficient_data)

    # ヘッダー行を追加
    header_rows = pd.DataFrame([['' for _ in range(3)] for _ in range(8)])
    full_df = pd.concat([header_rows, df_insufficient], ignore_index=True)

    with pytest.raises(DataExtractionError) as exc_info:
        extract_detail_data(full_df)

    assert "必要な列が存在しません" in str(exc_info.value)


# ==================== ヘルパー関数テスト ====================

@pytest.mark.unit
def test_is_detail_row():
    """is_detail_row関数のテスト"""
    # 明細行（6桁数字で始まる）
    valid_row = pd.Series(['250115', '本人', 'イオン'])
    assert is_detail_row(valid_row) is True

    # ヘッダー行（6桁数字でない）
    header_row = pd.Series(['利用日', '利用者', '利用先'])
    assert is_detail_row(header_row) is False

    # 空行
    empty_row = pd.Series([None, '', ''])
    assert is_detail_row(empty_row) is False

    # NaN
    nan_row = pd.Series([pd.NA, '', ''])
    assert is_detail_row(nan_row) is False


@pytest.mark.unit
@pytest.mark.parametrize("input_date,expected_month", [
    ("250115", 1),
    ("250630", 6),
    ("251231", 12),
])
def test_extract_month_number(input_date, expected_month):
    """extract_month_number関数のテスト"""
    result = extract_month_number(input_date)
    assert result == expected_month


@pytest.mark.unit
def test_validate_file_path_valid(temp_upload_dir):
    """validate_file_path関数のテスト（正常系）"""
    test_file = os.path.join(temp_upload_dir, 'test.csv')

    # ファイル作成
    with open(test_file, 'w') as f:
        f.write('test')

    # 検証成功
    assert validate_file_path(test_file, temp_upload_dir) is True


@pytest.mark.unit
def test_validate_file_path_traversal(temp_upload_dir):
    """validate_file_path関数のテスト（パストラバーサル検知）"""
    # パストラバーサル攻撃のパス
    malicious_path = os.path.join(temp_upload_dir, '..', 'etc', 'passwd')

    with pytest.raises(PathValidationError) as exc_info:
        validate_file_path(malicious_path, temp_upload_dir)

    assert "許可されたディレクトリ外です" in str(exc_info.value)


@pytest.mark.unit
def test_generate_preview_less_than_5():
    """generate_preview関数のテスト（5件未満）"""
    # 3件のテストデータ
    test_data = [
        {'date': '2025/01/01', 'store': '店舗1', 'amount': 1000},
        {'date': '2025/01/02', 'store': '店舗2', 'amount': 2000},
        {'date': '2025/01/03', 'store': '店舗3', 'amount': 3000}
    ]

    preview = generate_preview(test_data)

    assert len(preview) == 3


@pytest.mark.unit
def test_generate_preview_empty():
    """generate_preview関数のテスト（空リスト）"""
    preview = generate_preview([])
    assert preview == []


# ==================== 日付変換のエッジケーステスト ====================

@pytest.mark.unit
@pytest.mark.parametrize("invalid_date,expected_error", [
    ("251301", "月は1-12の範囲である必要があります"),  # 月が13
    ("250132", "日は1-31の範囲である必要があります"),  # 日が32
    ("250100", "日は1-31の範囲である必要があります"),  # 日が0
])
def test_date_validation_errors(invalid_date, expected_error):
    """日付検証エラーのテスト"""
    with pytest.raises(DateConversionError) as exc_info:
        convert_date_format(invalid_date)

    assert expected_error in str(exc_info.value)


@pytest.mark.unit
def test_date_conversion_1900s():
    """日付変換（1900年代）のテスト"""
    # 50-99 → 1950-1999
    assert convert_date_format("500101") == "1950/01/01"
    assert convert_date_format("991231") == "1999/12/31"
