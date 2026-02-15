"""
パフォーマンステスト

このモジュールはcategory_logic.pyのパフォーマンスをテストします。

テストケース:
1. 1000件レコードの処理時間測定（目標: 1秒以内）
2. 10000件レコードの処理時間測定（目標: 10秒以内）
3. メモリ使用量測定（目標: 100MB以内）
"""

import pytest
import json
import time
import sys
from pathlib import Path

from modules.category_logic import (
    load_mapping_data,
    determine_categories_batch,
    detect_unregistered_stores
)


@pytest.fixture
def sample_mapping_data():
    """パフォーマンステスト用マッピングデータ"""
    return {
        "version": "1.0",
        "mappings": [
            {
                "id": 1,
                "pattern": "ユニクロ",
                "match_type": "contains",
                "category": "衣類費",
                "column": "C",
                "priority": 3,
                "note": None
            },
            {
                "id": 2,
                "pattern": "セブンイレブン",
                "match_type": "contains",
                "category": "日用品費",
                "column": "D",
                "priority": 3,
                "note": None
            },
            {
                "id": 3,
                "pattern": "JR",
                "match_type": "startswith",
                "category": "交通費",
                "column": "E",
                "priority": 2,
                "note": None
            },
            {
                "id": 4,
                "pattern": "AMAZON",
                "match_type": "exact",
                "category": "ネット通販",
                "column": "F",
                "priority": 1,
                "note": None
            },
            {
                "id": 5,
                "pattern": "イオン",
                "match_type": "contains",
                "category": "食費",
                "column": "G",
                "priority": 3,
                "note": None
            }
        ]
    }


@pytest.fixture
def records_1000():
    """1000件のテストレコード"""
    test_data_path = Path('tests/test_data/sample_records_1000.json')
    if test_data_path.exists():
        with test_data_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # テストデータが存在しない場合は動的に生成
        stores = ['ユニクロ', 'セブンイレブン', 'JR東日本', 'AMAZON', 'イオン', '未登録店舗']
        return [
            {
                'date': f'2025/08/{(i % 28) + 1:02d}',
                'store': stores[i % len(stores)],
                'amount': (i * 100) % 10000
            }
            for i in range(1000)
        ]


@pytest.fixture
def records_10000():
    """10000件のテストレコード"""
    test_data_path = Path('tests/test_data/sample_records_10000.json')
    if test_data_path.exists():
        with test_data_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # テストデータが存在しない場合は動的に生成
        stores = ['ユニクロ', 'セブンイレブン', 'JR東日本', 'AMAZON', 'イオン', '未登録店舗']
        return [
            {
                'date': f'2025/08/{(i % 28) + 1:02d}',
                'store': stores[i % len(stores)],
                'amount': (i * 100) % 10000
            }
            for i in range(10000)
        ]


class TestPerformance1000Records:
    """テストケース1: 1000件レコードの処理時間測定（目標: 1秒以内）"""

    def test_determine_categories_batch_1000_records(self, sample_mapping_data, records_1000):
        """1000件のバッチ処理時間"""
        start_time = time.time()
        result = determine_categories_batch(records_1000, sample_mapping_data)
        elapsed_time = time.time() - start_time

        # 結果検証
        assert len(result) == 1000
        assert all('category' in record for record in result)
        assert all('column' in record for record in result)

        # パフォーマンス検証（目標: 1秒以内）
        print(f"\n1000件処理時間: {elapsed_time:.3f}秒")
        assert elapsed_time < 1.0, f"処理時間が目標を超えました: {elapsed_time:.3f}秒 > 1.0秒"

    def test_detect_unregistered_stores_1000_records(self, sample_mapping_data, records_1000):
        """1000件の未登録店舗検出時間"""
        start_time = time.time()
        result = detect_unregistered_stores(records_1000, sample_mapping_data)
        elapsed_time = time.time() - start_time

        # 結果検証
        assert isinstance(result, list)

        # パフォーマンス検証（目標: 1秒以内）
        print(f"\n1000件未登録店舗検出時間: {elapsed_time:.3f}秒")
        assert elapsed_time < 1.0, f"処理時間が目標を超えました: {elapsed_time:.3f}秒 > 1.0秒"


class TestPerformance10000Records:
    """テストケース2: 10000件レコードの処理時間測定（目標: 10秒以内）"""

    def test_determine_categories_batch_10000_records(self, sample_mapping_data, records_10000):
        """10000件のバッチ処理時間"""
        start_time = time.time()
        result = determine_categories_batch(records_10000, sample_mapping_data)
        elapsed_time = time.time() - start_time

        # 結果検証
        assert len(result) == 10000
        assert all('category' in record for record in result)
        assert all('column' in record for record in result)

        # パフォーマンス検証（目標: 10秒以内）
        print(f"\n10000件処理時間: {elapsed_time:.3f}秒")
        assert elapsed_time < 10.0, f"処理時間が目標を超えました: {elapsed_time:.3f}秒 > 10.0秒"

    def test_detect_unregistered_stores_10000_records(self, sample_mapping_data, records_10000):
        """10000件の未登録店舗検出時間"""
        start_time = time.time()
        result = detect_unregistered_stores(records_10000, sample_mapping_data)
        elapsed_time = time.time() - start_time

        # 結果検証
        assert isinstance(result, list)

        # パフォーマンス検証（目標: 10秒以内）
        print(f"\n10000件未登録店舗検出時間: {elapsed_time:.3f}秒")
        assert elapsed_time < 10.0, f"処理時間が目標を超えました: {elapsed_time:.3f}秒 > 10.0秒"


class TestMemoryUsage:
    """テストケース3: メモリ使用量測定（目標: 100MB以内）"""

    def test_memory_usage_1000_records(self, sample_mapping_data, records_1000):
        """1000件処理時のメモリ使用量"""
        # 処理前のメモリサイズを記録
        initial_size = sys.getsizeof(records_1000)

        # バッチ処理実行
        result = determine_categories_batch(records_1000, sample_mapping_data)

        # 処理後のメモリサイズを記録
        result_size = sys.getsizeof(result)

        # メモリ増加量を計算（バイト→MB）
        memory_increase_mb = (result_size - initial_size) / (1024 * 1024)

        print(f"\n1000件処理時のメモリ増加量: {memory_increase_mb:.2f}MB")
        print(f"  - 入力サイズ: {initial_size / 1024:.2f}KB")
        print(f"  - 出力サイズ: {result_size / 1024:.2f}KB")

        # メモリ増加量が100MB以内であることを確認
        assert memory_increase_mb < 100.0, f"メモリ使用量が目標を超えました: {memory_increase_mb:.2f}MB > 100MB"

    def test_memory_usage_10000_records(self, sample_mapping_data, records_10000):
        """10000件処理時のメモリ使用量"""
        # 処理前のメモリサイズを記録
        initial_size = sys.getsizeof(records_10000)

        # バッチ処理実行
        result = determine_categories_batch(records_10000, sample_mapping_data)

        # 処理後のメモリサイズを記録
        result_size = sys.getsizeof(result)

        # メモリ増加量を計算（バイト→MB）
        memory_increase_mb = (result_size - initial_size) / (1024 * 1024)

        print(f"\n10000件処理時のメモリ増加量: {memory_increase_mb:.2f}MB")
        print(f"  - 入力サイズ: {initial_size / 1024:.2f}KB")
        print(f"  - 出力サイズ: {result_size / 1024:.2f}KB")

        # メモリ増加量が100MB以内であることを確認
        assert memory_increase_mb < 100.0, f"メモリ使用量が目標を超えました: {memory_increase_mb:.2f}MB > 100MB"
