"""
Phase 4: カテゴリ決定・未登録店舗検出機能のテスト (pytest形式)

このモジュールは以下の関数のテストを実施します:
- determine_category(): 店舗名からカテゴリと列番号を決定
- detect_unregistered_stores(): 未登録店舗を検出し金額合計を算出
- determine_categories_batch(): 複数レコードのカテゴリを一括決定
"""

import pytest
from modules.category_logic import (
    load_mapping_data,
    determine_category,
    detect_unregistered_stores,
    determine_categories_batch
)


@pytest.fixture
def mapping_data():
    """テスト用のマッピングデータフィクスチャ"""
    return load_mapping_data('data/mapping.json')


class TestDetermineCategory:
    """determine_category()のテスト"""

    def test_registered_store_exact_match(self, mapping_data):
        """登録済み店舗（完全一致）のテスト"""
        result = determine_category("ユシンヤ", mapping_data)

        assert result['matched'] is True
        assert result['category'] == '外食費'
        assert result['column'] == 'C'
        assert result['pattern'] is not None
        assert result['match_type'] is not None

    def test_unregistered_store(self, mapping_data):
        """未登録店舗のテスト"""
        result = determine_category("存在しない店舗XYZ", mapping_data)

        assert result['matched'] is False
        assert result['category'] == '支払額'
        assert result['column'] == 'B'
        assert result['pattern'] is None
        assert result['match_type'] is None

    def test_partial_match(self, mapping_data):
        """部分一致のテスト"""
        result = determine_category("東京ユシンヤ池袋店", mapping_data)

        assert result['matched'] is True
        assert result['category'] is not None
        assert result['column'] is not None


class TestDetectUnregisteredStores:
    """detect_unregistered_stores()のテスト"""

    def test_multiple_unregistered_stores(self, mapping_data):
        """未登録店舗が複数ある場合のテスト"""
        records = [
            {'store': 'ユシンヤ', 'amount': 1000},  # 登録済み
            {'store': '未登録A', 'amount': 2000},    # 未登録
            {'store': '未登録A', 'amount': 3000},    # 未登録（同じ店舗）
            {'store': '未登録B', 'amount': 500},     # 未登録
            {'store': 'AMAZON', 'amount': 1500},     # 登録済み
        ]

        result = detect_unregistered_stores(records, mapping_data)

        assert len(result) == 2
        assert result[0]['store'] == '未登録A'
        assert result[0]['total_amount'] == 5000
        assert result[0]['count'] == 2
        assert result[1]['store'] == '未登録B'
        assert result[1]['total_amount'] == 500
        assert result[1]['count'] == 1

    def test_no_unregistered_stores(self, mapping_data):
        """未登録店舗がない場合のテスト"""
        records = [
            {'store': 'ユシンヤ', 'amount': 1000},
            {'store': 'AMAZON', 'amount': 1500},
        ]

        result = detect_unregistered_stores(records, mapping_data)

        assert len(result) == 0

    def test_empty_list(self, mapping_data):
        """空リストのテスト"""
        result = detect_unregistered_stores([], mapping_data)

        assert len(result) == 0
        assert isinstance(result, list)


class TestDetermineCategoriesBatch:
    """determine_categories_batch()のテスト"""

    def test_multiple_records(self, mapping_data):
        """複数レコードの一括処理テスト"""
        records = [
            {'date': '2025/08/15', 'store': 'ユシンヤ', 'amount': 5780},
            {'date': '2025/08/16', 'store': 'AMAZON', 'amount': 1200},
            {'date': '2025/08/17', 'store': '未登録店舗', 'amount': 3000},
        ]

        result = determine_categories_batch(records, mapping_data)

        assert len(result) == 3

        # 1件目（ユシンヤ）
        assert result[0]['store'] == 'ユシンヤ'
        assert result[0]['matched'] is True
        assert result[0]['category'] == '外食費'
        assert result[0]['column'] == 'C'
        assert result[0]['date'] == '2025/08/15'
        assert result[0]['amount'] == 5780

        # 2件目（AMAZON）
        assert result[1]['store'] == 'AMAZON'
        assert result[1]['matched'] is True

        # 3件目（未登録店舗）
        assert result[2]['store'] == '未登録店舗'
        assert result[2]['matched'] is False
        assert result[2]['category'] == '支払額'
        assert result[2]['column'] == 'B'

    def test_record_without_store_field(self, mapping_data):
        """storeフィールドがない場合のテスト"""
        records = [
            {'date': '2025/08/15', 'amount': 5780},  # storeフィールドなし
        ]

        result = determine_categories_batch(records, mapping_data)

        assert len(result) == 1
        assert result[0]['matched'] is False
        assert result[0]['category'] == '支払額'
        assert result[0]['column'] == 'B'

    def test_empty_records(self, mapping_data):
        """空のレコードリストのテスト"""
        result = determine_categories_batch([], mapping_data)

        assert len(result) == 0
        assert isinstance(result, list)
