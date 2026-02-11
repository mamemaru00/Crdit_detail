"""
Google Sheets API連携モジュール(sheets_api.py)のテストスイート

このテストスイートは以下のカテゴリをカバーします:
1. 認証テスト（5ケース）
2. スプレッドシート接続テスト（4ケース）
3. 年シート取得テスト（4ケース）
4. 月行番号計算テスト（4ケース）
5. 列番号変換テスト（4ケース）
6. セル値取得テスト（4ケース）
7. セル値更新テスト（5ケース）
8. バッチ更新テスト（5ケース）
9. レート制限対応テスト（3ケース）
10. エラーハンドリングテスト（2ケース）
11. 統合テスト（5ケース）

合計: 45テストケース
カバレッジ目標: 関数100%、分岐90%以上
"""

import json
import tempfile
import pytest
import time
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, Mock, patch, call

from modules.sheets_api import (
    authenticate,
    open_spreadsheet,
    get_year_sheet,
    get_month_row,
    get_column_index,
    get_cell_value,
    update_cell_value,
    batch_update_cells,
    _apply_rate_limit,
    _retry_on_api_error,
    AuthenticationError,
    SpreadsheetNotFoundError,
    SheetNotFoundError,
    CellUpdateError,
    SheetsAPIError,
    DEFAULT_CREDENTIALS_PATH,
    RATE_LIMIT_WAIT,
    MAX_RETRIES,
    MAX_BATCH_SIZE
)


# ==================== フィクスチャ ====================

@pytest.fixture
def mock_credentials():
    """モックの認証情報オブジェクト

    google.oauth2.service_account.Credentialsのモック

    Returns:
        MagicMock: モックの認証情報オブジェクト
    """
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False
    return mock_creds


@pytest.fixture
def mock_client():
    """モックのgspreadクライアント

    gspread.Clientのモック

    Returns:
        MagicMock: モックのgspreadクライアント
    """
    mock_client = MagicMock()
    mock_client.auth = None
    return mock_client


@pytest.fixture
def mock_spreadsheet():
    """モックのスプレッドシートオブジェクト

    gspread.Spreadsheetのモック

    Returns:
        MagicMock: モックのスプレッドシートオブジェクト
    """
    mock_sheet = MagicMock()
    mock_sheet.id = "test-spreadsheet-id"
    mock_sheet.title = "テスト家計簿"
    return mock_sheet


@pytest.fixture
def mock_worksheet():
    """モックのワークシートオブジェクト

    gspread.Worksheetのモック

    Returns:
        MagicMock: モックのワークシートオブジェクト
    """
    mock_ws = MagicMock()
    mock_ws.id = "test-worksheet-id"
    mock_ws.title = "2025年"
    return mock_ws


@pytest.fixture
def temp_credentials_file(tmp_path):
    """一時的な認証情報ファイル

    有効なJSONファイルを作成

    Args:
        tmp_path: pytestの一時ディレクトリ

    Returns:
        Path: 一時認証情報ファイルのパス
    """
    creds_file = tmp_path / "service_account.json"
    creds_data = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "12345",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test"
    }
    with creds_file.open('w', encoding='utf-8') as f:
        json.dump(creds_data, f, ensure_ascii=False, indent=2)
    return creds_file


@pytest.fixture
def sample_batch_updates():
    """バッチ更新用のサンプルデータ

    Returns:
        list[dict]: バッチ更新用のサンプルデータ
    """
    return [
        {'month': 8, 'column_letter': 'C', 'amount': 5780.0, 'add_mode': True},
        {'month': 8, 'column_letter': 'D', 'amount': 3200.0, 'add_mode': True},
        {'month': 9, 'column_letter': 'C', 'amount': 4500.0, 'add_mode': True}
    ]


@pytest.fixture
def mock_api_error_response():
    """APIError用のモックHTTPレスポンス

    gspread.exceptions.APIErrorはHTTPレスポンスオブジェクトを期待するため、
    json()とtextメソッドを持つモックを提供

    Returns:
        MagicMock: モックHTTPレスポンスオブジェクト
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "error": {
            "message": "API Error",
            "code": 500
        }
    }
    mock_response.text = "API Error"
    return mock_response


# ==================== 1. 認証テスト（5ケース） ====================

@patch('modules.sheets_api.gspread.authorize')
@patch('modules.sheets_api.Credentials.from_service_account_file')
def test_authenticate_success(mock_creds_from_file, mock_authorize, temp_credentials_file, mock_credentials, mock_client):
    """認証成功テスト

    正常な認証フローが実行されることを確認
    """
    # Mock設定
    mock_creds_from_file.return_value = mock_credentials
    mock_authorize.return_value = mock_client

    # 実行
    client = authenticate(temp_credentials_file)

    # 検証
    assert client is not None
    assert client == mock_client
    mock_creds_from_file.assert_called_once_with(
        str(temp_credentials_file),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    mock_authorize.assert_called_once_with(mock_credentials)


def test_authenticate_file_not_found():
    """認証情報ファイル未存在エラー

    ファイルが存在しない場合にAuthenticationErrorが発生することを確認
    """
    non_existent_path = Path("non_existent_path/service_account.json")

    with pytest.raises(AuthenticationError) as exc_info:
        authenticate(non_existent_path)

    assert "認証情報ファイルが見つかりません" in exc_info.value.message
    assert exc_info.value.details['path'] == str(non_existent_path)


def test_authenticate_invalid_json(tmp_path):
    """不正なJSON形式の認証情報ファイル

    JSON解析エラー時にAuthenticationErrorが発生することを確認
    """
    invalid_json_file = tmp_path / "invalid.json"
    invalid_json_file.write_text("{ invalid json }", encoding='utf-8')

    with patch('modules.sheets_api.Credentials.from_service_account_file') as mock_creds:
        mock_creds.side_effect = ValueError("Invalid JSON")

        with pytest.raises(AuthenticationError) as exc_info:
            authenticate(invalid_json_file)

        assert "認証情報ファイルのJSON解析に失敗しました" in exc_info.value.message


@patch('modules.sheets_api.gspread.authorize')
@patch('modules.sheets_api.Credentials.from_service_account_file')
def test_authenticate_custom_path(mock_creds_from_file, mock_authorize, temp_credentials_file, mock_credentials, mock_client):
    """カスタムパス指定での認証

    デフォルト以外のパスでの認証が正常に動作することを確認
    """
    mock_creds_from_file.return_value = mock_credentials
    mock_authorize.return_value = mock_client

    # カスタムパスで実行
    client = authenticate(temp_credentials_file)

    # 検証
    assert client is not None
    mock_creds_from_file.assert_called_once_with(
        str(temp_credentials_file),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )


@patch('modules.sheets_api.gspread.authorize')
@patch('modules.sheets_api.Credentials.from_service_account_file')
def test_authenticate_api_error(mock_creds_from_file, mock_authorize, temp_credentials_file, mock_credentials):
    """API認証エラー

    gspread.authorize()でエラーが発生した場合にAuthenticationErrorが発生することを確認
    """
    mock_creds_from_file.return_value = mock_credentials
    mock_authorize.side_effect = Exception("API authentication failed")

    with pytest.raises(AuthenticationError) as exc_info:
        authenticate(temp_credentials_file)

    assert "認証に失敗しました" in exc_info.value.message
    assert "API authentication failed" in str(exc_info.value.details['error'])


# ==================== 2. スプレッドシート接続テスト（4ケース） ====================

def test_open_spreadsheet_success(mock_client, mock_spreadsheet):
    """スプレッドシート接続成功

    正常にスプレッドシートを開けることを確認
    """
    mock_client.open_by_key.return_value = mock_spreadsheet

    result = open_spreadsheet(mock_client, "test-id")

    assert result == mock_spreadsheet
    assert result.title == "テスト家計簿"
    mock_client.open_by_key.assert_called_once_with("test-id")


def test_open_spreadsheet_not_found(mock_client):
    """スプレッドシート未検出エラー

    スプレッドシートが見つからない場合にSpreadsheetNotFoundErrorが発生することを確認
    """
    import gspread
    mock_client.open_by_key.side_effect = gspread.exceptions.SpreadsheetNotFound("Spreadsheet not found")

    with pytest.raises(SpreadsheetNotFoundError) as exc_info:
        open_spreadsheet(mock_client, "invalid-id")

    assert "スプレッドシートが見つかりません" in exc_info.value.message
    assert exc_info.value.details['spreadsheet_id'] == "invalid-id"


def test_open_spreadsheet_api_error(mock_client, mock_api_error_response):
    """APIエラー

    APIエラー発生時にSpreadsheetNotFoundErrorが発生することを確認
    """
    import gspread
    mock_client.open_by_key.side_effect = gspread.exceptions.APIError(mock_api_error_response)

    with pytest.raises(SpreadsheetNotFoundError) as exc_info:
        open_spreadsheet(mock_client, "error-id")

    assert "スプレッドシートへのアクセスに失敗しました" in exc_info.value.message


def test_open_spreadsheet_permission_error(mock_client):
    """権限エラー

    アクセス権限がない場合にSpreadsheetNotFoundErrorが発生することを確認
    """
    mock_client.open_by_key.side_effect = Exception("Permission denied")

    with pytest.raises(SpreadsheetNotFoundError) as exc_info:
        open_spreadsheet(mock_client, "permission-denied-id")

    assert "スプレッドシートの接続に失敗しました" in exc_info.value.message


# ==================== 3. 年シート取得テスト（4ケース） ====================

def test_get_year_sheet_success(mock_spreadsheet, mock_worksheet):
    """年シート取得成功（2025年）

    指定した年のシートが正常に取得できることを確認
    """
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    result = get_year_sheet(mock_spreadsheet, 2025)

    assert result == mock_worksheet
    assert result.title == "2025年"
    mock_spreadsheet.worksheet.assert_called_once_with("2025年")


def test_get_year_sheet_not_found(mock_spreadsheet):
    """年シート未検出エラー

    指定した年のシートが存在しない場合にSheetNotFoundErrorが発生することを確認
    """
    import gspread
    mock_spreadsheet.worksheet.side_effect = gspread.exceptions.WorksheetNotFound("Sheet not found")

    with pytest.raises(SheetNotFoundError) as exc_info:
        get_year_sheet(mock_spreadsheet, 2099)

    assert "年シートが見つかりません" in exc_info.value.message
    assert exc_info.value.details['year'] == 2099
    assert exc_info.value.details['sheet_name'] == "2099年"


@pytest.mark.parametrize("year,expected_sheet_name", [
    (2024, "2024年"),
    (2025, "2025年"),
    (2026, "2026年")
])
def test_get_year_sheet_different_years(mock_spreadsheet, mock_worksheet, year, expected_sheet_name):
    """複数年対応確認（2024, 2025, 2026）

    異なる年のシート取得が正しく動作することを確認
    """
    mock_worksheet.title = expected_sheet_name
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    result = get_year_sheet(mock_spreadsheet, year)

    assert result.title == expected_sheet_name
    mock_spreadsheet.worksheet.assert_called_once_with(expected_sheet_name)


def test_get_year_sheet_api_error(mock_spreadsheet):
    """APIエラー

    API呼び出しエラー時にSheetNotFoundErrorが発生することを確認
    """
    mock_spreadsheet.worksheet.side_effect = Exception("API Error")

    with pytest.raises(SheetNotFoundError) as exc_info:
        get_year_sheet(mock_spreadsheet, 2025)

    assert "年シートの取得に失敗しました" in exc_info.value.message


# ==================== 4. 月行番号計算テスト（4ケース） ====================

@pytest.mark.parametrize("month,expected_row", [
    (1, 4),    # 1月 → 4行目
    (2, 5),    # 2月 → 5行目
    (6, 9),    # 6月 → 9行目
    (8, 11),   # 8月 → 11行目
    (12, 15),  # 12月 → 15行目
])
def test_get_month_row_valid_months(month, expected_row):
    """全月（1～12）の行番号計算確認

    各月から正しい行番号が計算されることを確認
    """
    assert get_month_row(month) == expected_row


@pytest.mark.parametrize("invalid_month", [0, 13, -1, 100])
def test_get_month_row_out_of_range(invalid_month):
    """範囲外の月番号エラー（0, 13）

    月番号が範囲外の場合にValueErrorが発生することを確認
    """
    with pytest.raises(ValueError) as exc_info:
        get_month_row(invalid_month)

    assert "月番号が範囲外です" in str(exc_info.value)


@pytest.mark.parametrize("invalid_type", ["1", 1.5, None, [1], {"month": 1}])
def test_get_month_row_invalid_type(invalid_type):
    """型エラー（文字列、float、None等）

    月番号が整数以外の場合にValueErrorが発生することを確認
    """
    with pytest.raises(ValueError) as exc_info:
        get_month_row(invalid_type)

    assert "月番号は整数である必要があります" in str(exc_info.value)


@pytest.mark.parametrize("edge_month,expected_row", [
    (1, 4),   # 最小値（1月）
    (12, 15)  # 最大値（12月）
])
def test_get_month_row_edge_cases(edge_month, expected_row):
    """エッジケース（1月、12月）

    境界値が正しく計算されることを確認
    """
    assert get_month_row(edge_month) == expected_row


# ==================== 5. 列番号変換テスト（4ケース） ====================

@pytest.mark.parametrize("column_letter,expected_index", [
    ("B", 2),   # B列（支払額）
    ("C", 3),   # C列（外食費）
    ("D", 4),   # D列（日用品費）
    ("V", 22),  # V列（最後のカテゴリ）
])
def test_get_column_index_valid_columns(column_letter, expected_index):
    """有効列（B, C, V）の列番号変換

    各列名から正しい列番号が計算されることを確認
    """
    assert get_column_index(column_letter) == expected_index


@pytest.mark.parametrize("invalid_column,expected_message", [
    ("A", "列名が範囲外です"),  # A列は範囲外（C～V）
    ("B", "列名が範囲外です"),  # B列は月列のため範囲外（C～V）
    ("W", "列名が範囲外です"),  # W列は範囲外（C～V）
    ("Z", "列名が範囲外です"),  # Z列は範囲外（C～V）
    ("AA", "列名は1文字である必要があります")  # 2文字なので1文字チェックで弾かれる
])
def test_get_column_index_invalid_range(invalid_column, expected_message):
    """範囲外の列名エラー（A, W, Z, AA）

    列名が範囲外の場合にValueErrorが発生することを確認
    """
    with pytest.raises(ValueError) as exc_info:
        get_column_index(invalid_column)

    assert expected_message in str(exc_info.value)


@pytest.mark.parametrize("invalid_type", [2, None, [], {}])
def test_get_column_index_invalid_type(invalid_type):
    """型エラー（数値、None）

    列名が文字列以外の場合にValueErrorが発生することを確認
    """
    with pytest.raises(ValueError) as exc_info:
        get_column_index(invalid_type)

    assert "列名は文字列である必要があります" in str(exc_info.value)


@pytest.mark.parametrize("input_column,normalized_column,expected_index", [
    ("b", "B", 2),     # 小文字
    ("c", "C", 3),     # 小文字
    (" C ", "C", 3),   # 前後空白
])
def test_get_column_index_normalization(input_column, normalized_column, expected_index):
    """正規化（小文字、空白）

    入力が正規化されて正しく処理されることを確認
    """
    assert get_column_index(input_column) == expected_index


# ==================== 6. セル値取得テスト（4ケース） ====================

def test_get_cell_value_success(mock_worksheet):
    """セル値取得成功

    セルから正常に値を取得できることを確認
    """
    mock_cell = MagicMock()
    mock_cell.value = "12500"
    mock_worksheet.cell.return_value = mock_cell

    result = get_cell_value(mock_worksheet, 11, 2)

    assert result == 12500.0
    mock_worksheet.cell.assert_called_once_with(11, 2)


@pytest.mark.parametrize("empty_value", [None, "", "  "])
def test_get_cell_value_empty_cell(mock_worksheet, empty_value):
    """空セル処理（None, "", 空白）

    空セルの場合は0.0が返ることを確認
    """
    mock_cell = MagicMock()
    mock_cell.value = empty_value
    mock_worksheet.cell.return_value = mock_cell

    result = get_cell_value(mock_worksheet, 11, 2)

    assert result == 0.0


@pytest.mark.parametrize("cell_value,expected_float", [
    ("12500", 12500.0),
    ("12500.50", 12500.50),
    ("0", 0.0),
    (12500, 12500.0),
])
def test_get_cell_value_numeric_conversion(mock_worksheet, cell_value, expected_float):
    """数値変換（文字列→float）

    様々な形式の数値が正しくfloatに変換されることを確認
    """
    mock_cell = MagicMock()
    mock_cell.value = cell_value
    mock_worksheet.cell.return_value = mock_cell

    result = get_cell_value(mock_worksheet, 11, 2)

    assert result == expected_float


def test_get_cell_value_api_error(mock_worksheet, mock_api_error_response):
    """APIエラー

    API呼び出しエラー時にCellUpdateErrorが発生することを確認
    """
    import gspread
    mock_worksheet.cell.side_effect = gspread.exceptions.APIError(mock_api_error_response)

    with pytest.raises(CellUpdateError) as exc_info:
        get_cell_value(mock_worksheet, 11, 2)

    assert "セル値取得に失敗しました（API）" in exc_info.value.message
    assert exc_info.value.details['row'] == 11
    assert exc_info.value.details['column'] == 2


# ==================== 7. セル値更新テスト（5ケース） ====================

def test_update_cell_value_add_mode(mock_worksheet):
    """加算モード（デフォルト）

    既存値に金額が加算されることを確認
    """
    # 既存値取得のモック
    mock_cell = MagicMock()
    mock_cell.value = "12500"
    mock_worksheet.cell.return_value = mock_cell

    result = update_cell_value(mock_worksheet, 11, 2, 5780.0)

    # 検証
    assert result['row'] == 11
    assert result['column'] == 2
    assert result['old_value'] == 12500.0
    assert result['new_value'] == 18280.0
    assert result['added_amount'] == 5780.0

    # update_cellが新値で呼ばれたことを確認
    mock_worksheet.update_cell.assert_called_once_with(11, 2, 18280.0)


def test_update_cell_value_overwrite_mode(mock_worksheet):
    """上書きモード

    既存値を無視して新しい値で上書きされることを確認
    """
    mock_cell = MagicMock()
    mock_cell.value = "12500"
    mock_worksheet.cell.return_value = mock_cell

    result = update_cell_value(mock_worksheet, 11, 2, 5780.0, add_mode=False)

    # 検証
    assert result['old_value'] == 12500.0
    assert result['new_value'] == 5780.0
    assert result['added_amount'] == 5780.0

    # 上書きモードで更新されたことを確認
    mock_worksheet.update_cell.assert_called_once_with(11, 2, 5780.0)


def test_update_cell_value_empty_cell(mock_worksheet):
    """空セルへの加算（0 + amount）

    空セルに金額を加算すると、その金額がセットされることを確認
    """
    mock_cell = MagicMock()
    mock_cell.value = None
    mock_worksheet.cell.return_value = mock_cell

    result = update_cell_value(mock_worksheet, 11, 2, 5780.0)

    # 検証（0 + 5780 = 5780）
    assert result['old_value'] == 0.0
    assert result['new_value'] == 5780.0

    mock_worksheet.update_cell.assert_called_once_with(11, 2, 5780.0)


def test_update_cell_value_result_format(mock_worksheet):
    """戻り値形式確認

    戻り値が期待される形式であることを確認
    """
    mock_cell = MagicMock()
    mock_cell.value = "1000"
    mock_worksheet.cell.return_value = mock_cell

    result = update_cell_value(mock_worksheet, 4, 3, 2000.0)

    # 戻り値の形式確認
    assert isinstance(result, dict)
    assert 'row' in result
    assert 'column' in result
    assert 'old_value' in result
    assert 'new_value' in result
    assert 'added_amount' in result

    assert result['row'] == 4
    assert result['column'] == 3
    assert result['old_value'] == 1000.0
    assert result['new_value'] == 3000.0
    assert result['added_amount'] == 2000.0


def test_update_cell_value_api_error(mock_worksheet, mock_api_error_response):
    """APIエラー

    更新時のAPIエラーでCellUpdateErrorが発生することを確認
    """
    import gspread

    # 取得は成功、更新は失敗
    mock_cell = MagicMock()
    mock_cell.value = "1000"
    mock_worksheet.cell.return_value = mock_cell
    mock_worksheet.update_cell.side_effect = gspread.exceptions.APIError(mock_api_error_response)

    with pytest.raises(CellUpdateError) as exc_info:
        update_cell_value(mock_worksheet, 11, 2, 5780.0)

    assert "セル更新に失敗しました（API）" in exc_info.value.message


# ==================== 8. バッチ更新テスト（5ケース） ====================

@patch('modules.sheets_api.time.sleep')
def test_batch_update_cells_success(mock_sleep, mock_worksheet, sample_batch_updates):
    """バッチ更新成功（複数セル）

    複数セルが正常に更新されることを確認
    現在の実装はworksheet.update_cells()を使う一括更新モード
    """
    # batch_get()のモック（既存値取得用）
    mock_worksheet.batch_get.return_value = [
        [["1000"], ["2000"], ["3000"]]  # 3セル分の既存値
    ]

    result = batch_update_cells(mock_worksheet, sample_batch_updates)

    # 検証
    assert result['total_updates'] == 3
    assert result['successful_updates'] == 3
    assert result['failed_updates'] == 0
    assert len(result['update_details']) == 3
    assert len(result['errors']) == 0
    assert result['updated_cells'] == 3

    # update_cells()が1回だけ呼ばれることを確認（一括更新）
    mock_worksheet.update_cells.assert_called_once()

    # update_cell()は呼ばれない（個別更新ではない）
    mock_worksheet.update_cell.assert_not_called()

    # レート制限が1回だけ適用される
    assert mock_sleep.call_count == 1


def test_batch_update_cells_empty_list(mock_worksheet):
    """空リスト処理

    空リストの場合は何も更新されないことを確認
    """
    result = batch_update_cells(mock_worksheet, [])

    assert result['total_updates'] == 0
    assert result['successful_updates'] == 0
    assert result['failed_updates'] == 0
    assert len(result['update_details']) == 0
    assert len(result['errors']) == 0


def test_batch_update_cells_partial_failure(mock_worksheet):
    """部分的失敗（一部エラー）

    一部の更新が失敗しても、他の更新は継続されることを確認
    """
    updates = [
        {'month': 8, 'column_letter': 'C', 'amount': 5780.0, 'add_mode': True},
        {'month': 0, 'column_letter': 'C', 'amount': 3200.0, 'add_mode': True},  # 無効な月
        {'month': 9, 'column_letter': 'C', 'amount': 4500.0, 'add_mode': True},
    ]

    mock_cell = MagicMock()
    mock_cell.value = "1000"
    mock_worksheet.cell.return_value = mock_cell

    result = batch_update_cells(mock_worksheet, updates)

    # 検証
    assert result['total_updates'] == 3
    assert result['successful_updates'] == 2  # 1件目と3件目が成功
    assert result['failed_updates'] == 1      # 2件目が失敗
    assert len(result['errors']) == 1


def test_batch_update_cells_large_batch(mock_worksheet):
    """大量更新（100件超）の警告ログ確認

    MAX_BATCH_SIZEを超えても処理が継続されることを確認
    """
    large_updates = [
        {'month': (i % 12) + 1, 'column_letter': 'C', 'amount': 1000.0, 'add_mode': True}
        for i in range(150)
    ]

    mock_cell = MagicMock()
    mock_cell.value = "0"
    mock_worksheet.cell.return_value = mock_cell

    result = batch_update_cells(mock_worksheet, large_updates)

    # 検証（全て成功するはず）
    assert result['total_updates'] == 150
    assert result['successful_updates'] == 150


def test_batch_update_cells_result_format(mock_worksheet):
    """結果形式確認

    戻り値の形式が期待通りであることを確認
    """
    updates = [
        {'month': 8, 'column_letter': 'C', 'amount': 5780.0, 'add_mode': True}
    ]

    mock_cell = MagicMock()
    mock_cell.value = "1000"
    mock_worksheet.cell.return_value = mock_cell

    result = batch_update_cells(mock_worksheet, updates)

    # 形式確認
    assert isinstance(result, dict)
    assert 'total_updates' in result
    assert 'successful_updates' in result
    assert 'failed_updates' in result
    assert 'update_details' in result
    assert 'errors' in result

    # update_detailsの形式確認
    assert len(result['update_details']) == 1
    detail = result['update_details'][0]
    assert 'index' in detail
    assert 'month' in detail
    assert 'column_letter' in detail
    assert 'row' in detail
    assert 'column' in detail
    assert 'old_value' in detail
    assert 'new_value' in detail
    assert 'added_amount' in detail


# ==================== 9. レート制限対応テスト（3ケース） ====================

@patch('modules.sheets_api.time.sleep')
def test_apply_rate_limit(mock_sleep):
    """レート制限待機確認

    RATE_LIMIT_WAIT秒間待機することを確認
    """
    _apply_rate_limit()

    mock_sleep.assert_called_once_with(RATE_LIMIT_WAIT)


@patch('modules.sheets_api.time.sleep')
def test_batch_update_calls_rate_limit(mock_sleep, mock_worksheet):
    """バッチ更新がレート制限を呼ぶ

    一括更新後にレート制限が適用されることを確認
    現在の実装では一括更新のため、sleep()は1回のみ呼ばれる
    """
    updates = [
        {'month': 8, 'column_letter': 'C', 'amount': 5780.0, 'add_mode': True},
        {'month': 9, 'column_letter': 'C', 'amount': 3200.0, 'add_mode': True},
    ]

    # batch_get()のモック
    mock_worksheet.batch_get.return_value = [
        [["1000"], ["2000"]]  # 2セル分の既存値
    ]

    batch_update_cells(mock_worksheet, updates)

    # 一括更新後にsleep()が1回だけ呼ばれる
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_with(RATE_LIMIT_WAIT)


@patch('modules.sheets_api.time.sleep')
def test_rate_limit_timing(mock_sleep):
    """待機時間確認（time.sleep）

    正しい待機時間でsleep()が呼ばれることを確認
    """
    _apply_rate_limit()

    # RATE_LIMIT_WAITで呼ばれる
    mock_sleep.assert_called_with(1.0)


# ==================== 10. エラーハンドリングテスト（2ケース） ====================

def test_custom_exceptions():
    """カスタム例外クラスの動作確認

    各例外クラスが正しく動作することを確認
    """
    # SheetsAPIError
    base_error = SheetsAPIError("Base error", details={'key': 'value'})
    assert base_error.message == "Base error"
    assert base_error.details == {'key': 'value'}

    # AuthenticationError
    auth_error = AuthenticationError("Auth error", details={'path': 'test.json'})
    assert auth_error.message == "Auth error"
    assert auth_error.details == {'path': 'test.json'}
    assert isinstance(auth_error, SheetsAPIError)

    # SpreadsheetNotFoundError
    sheet_error = SpreadsheetNotFoundError("Sheet error")
    assert sheet_error.message == "Sheet error"
    assert isinstance(sheet_error, SheetsAPIError)

    # SheetNotFoundError
    worksheet_error = SheetNotFoundError("Worksheet error")
    assert worksheet_error.message == "Worksheet error"
    assert isinstance(worksheet_error, SheetsAPIError)

    # CellUpdateError
    cell_error = CellUpdateError("Cell error", details={'row': 1, 'col': 2})
    assert cell_error.message == "Cell error"
    assert cell_error.details == {'row': 1, 'col': 2}
    assert isinstance(cell_error, SheetsAPIError)


def test_error_details():
    """エラーdetails情報確認

    エラーオブジェクトのdetails属性が正しく設定されることを確認
    """
    details = {
        'spreadsheet_id': 'test-id',
        'sheet_name': '2025年',
        'row': 11,
        'column': 3,
        'error': 'Test error message'
    }

    error = CellUpdateError("Test error", details=details)

    assert error.details['spreadsheet_id'] == 'test-id'
    assert error.details['sheet_name'] == '2025年'
    assert error.details['row'] == 11
    assert error.details['column'] == 3
    assert error.details['error'] == 'Test error message'


# ==================== 11. 統合テスト（5ケース） ====================

@patch('modules.sheets_api.gspread.authorize')
@patch('modules.sheets_api.Credentials.from_service_account_file')
def test_full_workflow_single_cell(mock_creds_from_file, mock_authorize, temp_credentials_file,
                                    mock_credentials, mock_client, mock_spreadsheet, mock_worksheet):
    """完全ワークフロー（認証→更新）

    認証から単一セル更新までの完全なフローを確認
    """
    # Mock設定
    mock_creds_from_file.return_value = mock_credentials
    mock_authorize.return_value = mock_client
    mock_client.open_by_key.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    mock_cell = MagicMock()
    mock_cell.value = "5000"
    mock_worksheet.cell.return_value = mock_cell

    # 1. 認証
    client = authenticate(temp_credentials_file)
    assert client is not None

    # 2. スプレッドシート接続
    spreadsheet = open_spreadsheet(client, "test-id")
    assert spreadsheet == mock_spreadsheet

    # 3. 年シート取得
    worksheet = get_year_sheet(spreadsheet, 2025)
    assert worksheet == mock_worksheet

    # 4. 月行番号計算
    row = get_month_row(8)
    assert row == 11

    # 5. 列番号計算
    col = get_column_index('C')
    assert col == 3

    # 6. セル更新
    result = update_cell_value(worksheet, row, col, 2000.0)
    assert result['old_value'] == 5000.0
    assert result['new_value'] == 7000.0


@patch('modules.sheets_api.gspread.authorize')
@patch('modules.sheets_api.Credentials.from_service_account_file')
def test_full_workflow_batch(mock_creds_from_file, mock_authorize, temp_credentials_file,
                             mock_credentials, mock_client, mock_spreadsheet, mock_worksheet):
    """バッチ更新ワークフロー

    認証からバッチ更新までの完全なフローを確認
    """
    # Mock設定
    mock_creds_from_file.return_value = mock_credentials
    mock_authorize.return_value = mock_client
    mock_client.open_by_key.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    mock_cell = MagicMock()
    mock_cell.value = "1000"
    mock_worksheet.cell.return_value = mock_cell

    # 認証→接続→シート取得
    client = authenticate(temp_credentials_file)
    spreadsheet = open_spreadsheet(client, "test-id")
    worksheet = get_year_sheet(spreadsheet, 2025)

    # バッチ更新
    updates = [
        {'month': 8, 'column_letter': 'C', 'amount': 5780.0, 'add_mode': True},
        {'month': 9, 'column_letter': 'D', 'amount': 3200.0, 'add_mode': True},
    ]

    result = batch_update_cells(worksheet, updates)

    assert result['successful_updates'] == 2
    assert result['failed_updates'] == 0


def test_multiple_months_update(mock_worksheet):
    """複数月更新

    異なる月への更新が正しく処理されることを確認
    """
    updates = [
        {'month': 1, 'column_letter': 'C', 'amount': 1000.0, 'add_mode': True},
        {'month': 6, 'column_letter': 'C', 'amount': 2000.0, 'add_mode': True},
        {'month': 12, 'column_letter': 'C', 'amount': 3000.0, 'add_mode': True},
    ]

    mock_cell = MagicMock()
    mock_cell.value = "0"
    mock_worksheet.cell.return_value = mock_cell

    result = batch_update_cells(mock_worksheet, updates)

    assert result['successful_updates'] == 3

    # 各月の行番号が正しく計算されていることを確認
    details = result['update_details']
    assert details[0]['row'] == 4   # 1月
    assert details[1]['row'] == 9   # 6月
    assert details[2]['row'] == 15  # 12月


def test_multiple_categories_update(mock_worksheet):
    """複数カテゴリ更新

    異なるカテゴリへの更新が正しく処理されることを確認
    """
    updates = [
        {'month': 8, 'column_letter': 'B', 'amount': 1000.0, 'add_mode': True},  # 支払額
        {'month': 8, 'column_letter': 'C', 'amount': 2000.0, 'add_mode': True},  # 外食費
        {'month': 8, 'column_letter': 'V', 'amount': 3000.0, 'add_mode': True},  # その他
    ]

    mock_cell = MagicMock()
    mock_cell.value = "0"
    mock_worksheet.cell.return_value = mock_cell

    result = batch_update_cells(mock_worksheet, updates)

    assert result['successful_updates'] == 3

    # 各カテゴリの列番号が正しく計算されていることを確認
    details = result['update_details']
    assert details[0]['column'] == 2   # B列
    assert details[1]['column'] == 3   # C列
    assert details[2]['column'] == 22  # V列


def test_error_recovery(mock_worksheet):
    """エラーリカバリー

    一部のセル更新が失敗しても、他のセルは更新されることを確認
    """
    updates = [
        {'month': 8, 'column_letter': 'C', 'amount': 1000.0, 'add_mode': True},
        {'month': 99, 'column_letter': 'C', 'amount': 2000.0, 'add_mode': True},  # エラー
        {'month': 9, 'column_letter': 'C', 'amount': 3000.0, 'add_mode': True},
        {'month': 10, 'column_letter': 'Z', 'amount': 4000.0, 'add_mode': True},  # エラー
        {'month': 11, 'column_letter': 'C', 'amount': 5000.0, 'add_mode': True},
    ]

    mock_cell = MagicMock()
    mock_cell.value = "0"
    mock_worksheet.cell.return_value = mock_cell

    result = batch_update_cells(mock_worksheet, updates)

    # 3件成功、2件失敗
    assert result['total_updates'] == 5
    assert result['successful_updates'] == 3
    assert result['failed_updates'] == 2
    assert len(result['errors']) == 2


# ==================== カバレッジ向上用テスト ====================

def test_get_cell_value_non_numeric(mock_worksheet):
    """数値以外のセル値でエラー

    数値に変換できない値の場合にCellUpdateErrorが発生することを確認
    """
    mock_cell = MagicMock()
    mock_cell.value = "非数値"
    mock_worksheet.cell.return_value = mock_cell

    with pytest.raises(CellUpdateError) as exc_info:
        get_cell_value(mock_worksheet, 11, 2)

    assert "セル値の数値変換に失敗しました" in exc_info.value.message


def test_batch_update_missing_field(mock_worksheet):
    """バッチ更新で必須フィールド不足

    必須フィールドが不足している場合にエラーとして記録されることを確認
    """
    updates = [
        {'month': 8, 'amount': 1000.0},  # column_letterが不足
    ]

    result = batch_update_cells(mock_worksheet, updates)

    assert result['failed_updates'] == 1
    assert len(result['errors']) == 1
    assert '必須フィールドがありません' in result['errors'][0]['error']


def test_get_column_index_multi_char(mock_worksheet):
    """複数文字の列名エラー

    複数文字の列名でValueErrorが発生することを確認
    """
    with pytest.raises(ValueError) as exc_info:
        get_column_index("AB")

    assert "列名は1文字である必要があります" in str(exc_info.value)


@patch('modules.sheets_api.time.sleep')
def test_retry_decorator(mock_sleep, mock_api_error_response):
    """リトライデコレータの動作確認

    _retry_on_api_errorデコレータが正しく動作することを確認
    """
    import gspread

    @_retry_on_api_error(max_retries=3)
    def failing_function():
        raise gspread.exceptions.APIError(mock_api_error_response)

    # 3回リトライ後に例外が発生することを確認
    with pytest.raises(gspread.exceptions.APIError):
        failing_function()

    # リトライ間のsleep()呼び出し確認（1秒、2秒）
    assert mock_sleep.call_count == 2  # 最後のリトライではsleepしない


def test_sheets_api_error_no_details():
    """details なしのエラー作成

    detailsを指定しない場合に空の辞書がセットされることを確認
    """
    error = SheetsAPIError("Test error")

    assert error.message == "Test error"
    assert error.details == {}
    assert isinstance(error.details, dict)
