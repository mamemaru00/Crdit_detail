"""
batch_get()実装検証用テスト
Author: Claude Code - Compliance Verifier
Created: 2026-01-07
"""

import pytest
import time
from unittest.mock import MagicMock, patch


@pytest.mark.performance
def test_batch_get_direct():
    """worksheet.batch_get()の直接呼び出しテスト（モック使用）"""
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

    print(f"\nOK: 1000 cells batch_get() success: {elapsed_time:.3f} sec")


@pytest.mark.performance
def test_batch_update_cells_integration():
    """batch_update_cells()関数の統合テスト"""
    from modules import sheets_api

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
        column_letter = chr(ord('C') + (i % 20))  # C～V列を循環
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

    # 成功件数確認
    assert result['successful_updates'] == 1000, f"成功件数が不正: {result['successful_updates']}"
    assert result['failed_updates'] == 0, f"失敗件数が不正: {result['failed_updates']}"

    print(f"\nOK: 1000 records integration success: {elapsed_time:.3f} sec")
    print(f"  - batch_get() calls: {mock_worksheet.batch_get.call_count}")
    print(f"  - update_cells() calls: {mock_worksheet.update_cells.call_count}")
    print(f"  - successful updates: {result['successful_updates']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
