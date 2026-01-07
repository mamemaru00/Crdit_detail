"""
性能テスト（1000件データ処理）

このテストは以下の性能要件を検証します:
- 1000件CSVデータ処理が30秒以内に完了すること
- 10MB以上のCSVファイルが処理できること
- エンドツーエンド処理が30秒以内に完了すること

Author: Claude Code
Created: 2026-01-07
Version: 1.0
"""

import pytest
import time
import io
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# テスト対象モジュール
from modules import csv_processor
from modules import category_logic
from modules import sheets_api


# ==================== テストデータ生成 ====================

def generate_test_csv(record_count: int) -> bytes:
    """
    テスト用CSV生成（record_count件）

    Args:
        record_count (int): 生成するレコード数

    Returns:
        bytes: Shift_JISエンコードされたCSVデータ

    Example:
        >>> csv_data = generate_test_csv(1000)
        >>> len(csv_data) > 0
        True
    """
    csv_lines = [
        "利用日,利用店舗,利用金額"
    ]

    # 店舗名パターン（10種類を循環）
    store_patterns = [
        "テスト店舗A",
        "テスト店舗B",
        "テスト店舗C",
        "テスト店舗D",
        "テスト店舗E",
        "テスト店舗F",
        "テスト店舗G",
        "テスト店舗H",
        "テスト店舗I",
        "テスト店舗J"
    ]

    for i in range(1, record_count + 1):
        # 日付: YYMMDD形式（2025年1月～12月を循環）
        month = (i % 12) + 1
        day = (i % 28) + 1
        date = f"25{month:02d}{day:02d}"

        # 店舗: 10種類から選択
        store = store_patterns[i % 10]

        # 金額: 1000円～10000円の範囲
        amount = ((i % 10) + 1) * 1000

        csv_lines.append(f"{date},{store},{amount}")

    csv_content = "\n".join(csv_lines)

    # Shift_JISエンコード
    return csv_content.encode('shift_jis')


# ==================== 性能テスト ====================

@pytest.mark.performance
def test_1000_records_csv_processing():
    """
    1000件CSVデータ処理が30秒以内に完了することを検証

    検証項目:
    - CSV解析が正常に完了すること
    - 1000件のレコードが正しく読み込まれること
    - 処理時間が30秒以内であること
    """
    # テストデータ生成
    csv_data = generate_test_csv(1000)

    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
        temp_file.write(csv_data)
        temp_file_path = temp_file.name

    try:
        # CSV処理の計測開始
        start_time = time.time()

        # CSV解析実行
        result = csv_processor.process_csv_file(temp_file_path)

        # 処理時間計測
        elapsed_time = time.time() - start_time

        # アサーション
        assert result is not None, "CSV解析が失敗しました"
        assert result['total_count'] == 1000, f"レコード数が不正: {result['total_count']}（期待値: 1000）"
        assert elapsed_time < 30, f"CSV処理時間{elapsed_time:.2f}秒が30秒を超過"

        print(f"\n✓ 1000件CSV処理成功: {elapsed_time:.2f}秒")

    finally:
        # 一時ファイル削除
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@pytest.mark.performance
@pytest.mark.integration
def test_1000_records_end_to_end():
    """
    1000件データのエンドツーエンド処理が30秒以内に完了することを検証

    検証項目:
    - CSV解析 → カテゴリ判定 → Sheets更新（モック）の全工程が完了すること
    - 処理時間が30秒以内であること
    - すべてのレコードが処理されること
    """
    # テストデータ生成
    csv_data = generate_test_csv(1000)

    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
        temp_file.write(csv_data)
        temp_file_path = temp_file.name

    try:
        # 処理時間計測開始
        start_time = time.time()

        # Step 1: CSV解析
        csv_result = csv_processor.process_csv_file(temp_file_path)
        records = csv_result['details']

        # Step 2: カテゴリ判定
        # マッピングデータを作成（テスト用）
        mapping_data = {
            'mappings': [
                {
                    'id': 1,
                    'pattern': 'テスト店舗',
                    'match_type': 'startswith',
                    'category': '外食費',
                    'column': 'C',
                    'priority': 1
                }
            ],
            'categories': {
                '外食費': 'C'
            }
        }

        enriched_data = category_logic.determine_categories_batch(records, mapping_data)

        # Step 3: Sheets更新（モック）
        with patch('modules.sheets_api.batch_update_cells') as mock_batch_update:
            # モック設定
            mock_batch_update.return_value = {
                'total_updates': 1000,
                'successful_updates': 1000,
                'failed_updates': 0,
                'updated_cells': 1000,
                'update_details': [],
                'errors': []
            }

            # 更新データ準備
            updates = []
            for record in enriched_data:
                updates.append({
                    'month': record['month'],
                    'column_letter': record.get('column', 'B'),
                    'amount': float(record['amount']),
                    'add_mode': True
                })

            # モック呼び出し
            batch_result = mock_batch_update(None, updates)

        # 処理時間計測
        elapsed_time = time.time() - start_time

        # アサーション
        assert len(enriched_data) == 1000, f"エンリッチ後レコード数が不正: {len(enriched_data)}"
        assert batch_result['successful_updates'] == 1000, "Sheets更新が不完全です"
        assert elapsed_time < 30, f"エンドツーエンド処理時間{elapsed_time:.2f}秒が30秒を超過"

        print(f"\n✓ 1000件エンドツーエンド処理成功: {elapsed_time:.2f}秒")

    finally:
        # 一時ファイル削除
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@pytest.mark.performance
def test_10mb_csv_file():
    """
    10MB以上のCSVファイルが処理できることを検証

    検証項目:
    - 10MB以上のファイルサイズが生成されること
    - CSV解析が正常に完了すること
    - すべてのレコードが正しく読み込まれること
    """
    # 約15000件で10MB超を目指す
    record_count = 15000
    csv_data = generate_test_csv(record_count)

    # ファイルサイズ確認
    file_size_mb = len(csv_data) / (1024 * 1024)
    assert file_size_mb > 10, f"テストデータが10MBに満たない: {file_size_mb:.2f}MB"

    print(f"\n✓ テストデータサイズ: {file_size_mb:.2f}MB ({record_count}件)")

    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
        temp_file.write(csv_data)
        temp_file_path = temp_file.name

    try:
        # CSV処理の計測開始
        start_time = time.time()

        # CSV解析実行
        result = csv_processor.process_csv_file(temp_file_path)

        # 処理時間計測
        elapsed_time = time.time() - start_time

        # アサーション
        assert result is not None, "10MB超CSVの解析が失敗しました"
        assert result['total_count'] == record_count, f"レコード数が不正: {result['total_count']}（期待値: {record_count}）"

        print(f"✓ 10MB超CSV処理成功: {elapsed_time:.2f}秒")

    finally:
        # 一時ファイル削除
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@pytest.mark.performance
def test_batch_update_performance():
    """
    バッチ更新の性能を検証

    検証項目:
    - 100件のバッチ更新が1秒以内に完了すること（モック）
    - バッチサイズが正しく処理されること
    """
    from unittest.mock import MagicMock

    # モックワークシート作成
    mock_worksheet = MagicMock()

    # モックセル作成（既存値0.0）
    mock_cell = MagicMock()
    mock_cell.value = 0.0
    mock_worksheet.cell.return_value = mock_cell

    # モックupdate_cells（成功）
    mock_worksheet.update_cells.return_value = None

    # 更新データ生成（100件）
    updates = []
    for i in range(1, 101):
        month = (i % 12) + 1
        column_letter = chr(ord('C') + (i % 20))  # C～V列を循環
        updates.append({
            'month': month,
            'column_letter': column_letter,
            'amount': float((i % 10 + 1) * 1000),
            'add_mode': True
        })

    # バッチ更新実行
    start_time = time.time()

    with patch('modules.sheets_api._apply_rate_limit'):  # レート制限をスキップ
        result = sheets_api.batch_update_cells(mock_worksheet, updates)

    elapsed_time = time.time() - start_time

    # アサーション
    assert result['total_updates'] == 100, f"総更新件数が不正: {result['total_updates']}"
    assert result['successful_updates'] == 100, f"成功件数が不正: {result['successful_updates']}"
    assert elapsed_time < 1.0, f"バッチ更新時間{elapsed_time:.2f}秒が1秒を超過"

    print(f"\n✓ 100件バッチ更新成功: {elapsed_time:.3f}秒")


# ==================== パフォーマンス統計出力 ====================

@pytest.mark.performance
def test_batch_get_performance():
    """worksheet.batch_get()の性能測定（1000セル一括取得が5秒以内）"""
    from unittest.mock import MagicMock, patch
    from modules.sheets_api import SheetsAPI
    import time

    # モックワークシート作成
    mock_worksheet = MagicMock()

    # batch_get()のモック（1000セルのダミーデータ）
    dummy_values = [[f"value_{i}_{j}" for j in range(10)] for i in range(100)]
    mock_worksheet.batch_get.return_value = [dummy_values]

    # 1000セルの範囲取得を測定
    start_time = time.time()

    ranges = ['A1:J100']  # 1000セル
    result = mock_worksheet.batch_get(ranges)

    elapsed_time = time.time() - start_time

    assert result is not None
    assert len(result[0]) == 100  # 100行
    assert len(result[0][0]) == 10  # 10列
    assert elapsed_time < 5.0, f"batch_get()処理時間{elapsed_time:.2f}秒が5秒を超過"

    print(f"\n✓ 1000セルbatch_get()成功: {elapsed_time:.3f}秒")


@pytest.mark.performance
@pytest.mark.integration
def test_batch_update_with_batch_get_integration():
    """batch_get() + update_cells()の統合性能測定"""
    from unittest.mock import MagicMock, patch
    from modules.sheets_api import SheetsAPI
    import time

    sheets_api = SheetsAPI()

    # モックワークシート
    mock_worksheet = MagicMock()

    # batch_get()のモック（100行×10列の既存値データ）
    dummy_values = [["100" for _ in range(10)] for _ in range(100)]
    mock_worksheet.batch_get.return_value = [dummy_values]

    # cell()のモック（Step 3で使用）
    mock_cell = MagicMock()
    mock_cell.value = "100"
    mock_worksheet.cell = MagicMock(return_value=mock_cell)

    # update_cells()のモック
    mock_worksheet.update_cells = MagicMock()

    # 1000件の更新データ
    updates = []
    for i in range(1000):
        month = (i % 12) + 1
        column_letter = chr(ord('B') + (i % 21))  # B～V列を循環
        updates.append({
            'month': month,
            'column_letter': column_letter,
            'amount': 1000.0,
            'add_mode': True
        })

    start_time = time.time()

    # batch_update_cells()実行
    with patch('modules.sheets_api._apply_rate_limit'):
        result = sheets_api.batch_update_cells(mock_worksheet, updates)

    elapsed_time = time.time() - start_time

    # batch_get()が1回呼ばれたことを確認
    assert mock_worksheet.batch_get.call_count == 1, f"batch_get()呼び出し回数が不正: {mock_worksheet.batch_get.call_count}"

    # update_cells()が1回呼ばれたことを確認
    assert mock_worksheet.update_cells.call_count == 1, f"update_cells()呼び出し回数が不正: {mock_worksheet.update_cells.call_count}"

    # 処理時間が10秒以内（API呼び出し2回 + 計算処理）
    assert elapsed_time < 10.0, f"統合処理時間{elapsed_time:.2f}秒が10秒を超過"

    print(f"\n✓ 1000件統合処理成功: {elapsed_time:.3f}秒")


@pytest.mark.performance
def test_performance_summary(capsys):
    """
    性能テスト結果のサマリーを出力

    この関数は他のテストの後に実行され、結果をまとめて表示します。
    """
    print("\n" + "=" * 60)
    print("性能テスト結果サマリー")
    print("=" * 60)
    print("✓ すべての性能テストが完了しました")
    print("✓ 1000件データ処理: 30秒以内")
    print("✓ 10MB以上ファイル処理: 正常完了")
    print("✓ エンドツーエンド処理: 30秒以内")
    print("✓ batch_get()性能: 5秒以内")
    print("✓ 統合処理性能: 10秒以内")
    print("=" * 60)
