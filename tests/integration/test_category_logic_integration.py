"""
統合テスト

このモジュールはcategory_logic.pyの統合的な動作をテストします。

テストケース:
1. 実際のマッピングデータ読込 → カテゴリ判定の連携
2. マッピングデータ変更後の再読込・再判定
3. 複数カテゴリの混在データ処理
4. 全レコード未登録の場合
5. 全レコード登録済みの場合
"""

import pytest
import json
import tempfile
from pathlib import Path

from modules.category_logic import (
    load_mapping_data,
    determine_category,
    detect_unregistered_stores,
    determine_categories_batch,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_STARTSWITH,
    MATCH_TYPE_CONTAINS
)


@pytest.fixture
def real_mapping_data():
    """実際のdata/mapping.jsonを読み込む"""
    return load_mapping_data('data/mapping.json')


class TestRealMappingDataIntegration:
    """テストケース1: 実際のマッピングデータ読込 → カテゴリ判定の連携"""

    def test_load_real_mapping_and_determine(self, real_mapping_data):
        """実際のマッピングファイルを読み込み、カテゴリ判定を行う"""
        # マッピングデータが正常に読み込まれていることを確認
        assert 'version' in real_mapping_data
        assert 'mappings' in real_mapping_data
        # Phase 7: デフォルト設定は廃止（ChatGPT分類フローに統合）
        # assert 'default' in real_mapping_data  # 削除済み
        assert len(real_mapping_data['mappings']) > 0

        # マッピングに登録されている店舗名で判定
        # data/mapping.jsonに"ユシンヤ"が登録されていることを前提
        result = determine_category("ユシンヤ", real_mapping_data)
        assert result['matched'] is True
        assert result['category'] is not None
        assert result['column'] is not None

    def test_batch_processing_with_real_data(self, real_mapping_data):
        """実際のマッピングデータでバッチ処理を行う"""
        records = [
            {'date': '2025/08/15', 'store': 'ユシンヤ', 'amount': 5780},
            {'date': '2025/08/16', 'store': 'AMAZON', 'amount': 1200},
            {'date': '2025/08/17', 'store': 'イオン', 'amount': 3000},
        ]

        result = determine_categories_batch(records, real_mapping_data)

        # 全レコードが処理されることを確認
        assert len(result) == 3

        # 各レコードがcategoryとcolumnを持つことを確認
        for record in result:
            assert 'category' in record
            assert 'column' in record
            assert 'matched' in record


class TestMappingDataReload:
    """テストケース2: マッピングデータ変更後の再読込・再判定"""

    def test_mapping_data_reload_and_rejudge(self):
        """マッピングデータを変更して再読込・再判定する"""
        # 一時マッピングデータ1を作成（Phase 7: default削除）
        mapping_data_1 = {
            "version": "2.0",
            "mappings": [
                {
                    "id": 1,
                    "pattern": "テスト店舗A",
                    "match_type": MATCH_TYPE_EXACT,
                    "category": "カテゴリA",
                    "column": "C",
                    "priority": 1,
                    "note": None
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mapping_data_1, f, ensure_ascii=False, indent=2)
            temp_file = f.name

        try:
            # マッピング1を読み込み
            data_1 = load_mapping_data(temp_file)
            result_1 = determine_category("テスト店舗A", data_1)
            assert result_1['matched'] is True
            assert result_1['category'] == 'カテゴリA'

            # マッピングデータを変更
            mapping_data_2 = {
                "version": "2.0",
                "mappings": [
                    {
                        "id": 1,
                        "pattern": "テスト店舗A",
                        "match_type": MATCH_TYPE_EXACT,
                        "category": "カテゴリB",  # カテゴリを変更
                        "column": "D",  # 列も変更
                        "priority": 1,
                        "note": None
                    }
                ],
                "default": {"category": "支払額", "column": "B"}
            }

            # ファイルを上書き
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(mapping_data_2, f, ensure_ascii=False, indent=2)

            # 再読込
            data_2 = load_mapping_data(temp_file)
            result_2 = determine_category("テスト店舗A", data_2)

            # 変更が反映されていることを確認
            assert result_2['matched'] is True
            assert result_2['category'] == 'カテゴリB'
            assert result_2['column'] == 'D'

        finally:
            Path(temp_file).unlink(missing_ok=True)


class TestMultipleCategoriesMixedData:
    """テストケース3: 複数カテゴリの混在データ処理"""

    def test_multiple_categories_mixed_processing(self):
        """複数カテゴリが混在するデータの処理"""
        mapping_data = {
            "version": "1.0",
            "mappings": [
                {
                    "id": 1,
                    "pattern": "ユニクロ",
                    "match_type": MATCH_TYPE_CONTAINS,
                    "category": "衣類費",
                    "column": "C",
                    "priority": 3,
                    "note": None
                },
                {
                    "id": 2,
                    "pattern": "セブンイレブン",
                    "match_type": MATCH_TYPE_CONTAINS,
                    "category": "日用品費",
                    "column": "D",
                    "priority": 3,
                    "note": None
                },
                {
                    "id": 3,
                    "pattern": "JR",
                    "match_type": MATCH_TYPE_STARTSWITH,
                    "category": "交通費",
                    "column": "E",
                    "priority": 2,
                    "note": None
                }
            ],
            "default": {"category": "支払額", "column": "B"}
        }

        records = [
            {'date': '2025/08/15', 'store': 'ユニクロ池袋店', 'amount': 5000},
            {'date': '2025/08/16', 'store': 'セブンイレブン新宿店', 'amount': 1200},
            {'date': '2025/08/17', 'store': 'JR東日本', 'amount': 3000},
            {'date': '2025/08/18', 'store': '未登録店舗', 'amount': 2000},
        ]

        result = determine_categories_batch(records, mapping_data)

        # カテゴリごとに正しく振り分けられることを確認
        assert result[0]['category'] == '衣類費'
        assert result[0]['column'] == 'C'
        assert result[0]['matched'] is True

        assert result[1]['category'] == '日用品費'
        assert result[1]['column'] == 'D'
        assert result[1]['matched'] is True

        assert result[2]['category'] == '交通費'
        assert result[2]['column'] == 'E'
        assert result[2]['matched'] is True

        assert result[3]['category'] is None
        assert result[3]['column'] is None
        assert result[3]['matched'] is False


class TestAllRecordsUnregistered:
    """テストケース4: 全レコード未登録の場合"""

    def test_all_records_unregistered(self):
        """全レコードが未登録店舗の場合"""
        mapping_data = {
            "version": "1.0",
            "mappings": [
                {
                    "id": 1,
                    "pattern": "登録店舗",
                    "match_type": MATCH_TYPE_EXACT,
                    "category": "テストカテゴリ",
                    "column": "C",
                    "priority": 1,
                    "note": None
                }
            ],
            "default": {"category": "支払額", "column": "B"}
        }

        records = [
            {'store': '未登録店舗A', 'amount': 1000},
            {'store': '未登録店舗B', 'amount': 2000},
            {'store': '未登録店舗C', 'amount': 3000},
        ]

        # バッチ処理
        result_batch = determine_categories_batch(records, mapping_data)
        assert len(result_batch) == 3
        for record in result_batch:
            assert record['matched'] is False
            assert record['category'] is None
            assert record['column'] is None

        # 未登録店舗検出
        unregistered = detect_unregistered_stores(records, mapping_data)
        assert len(unregistered) == 3

        # 金額降順でソートされていることを確認
        assert unregistered[0]['total_amount'] == 3000
        assert unregistered[1]['total_amount'] == 2000
        assert unregistered[2]['total_amount'] == 1000


class TestAllRecordsRegistered:
    """テストケース5: 全レコード登録済みの場合"""

    def test_all_records_registered(self):
        """全レコードが登録済み店舗の場合"""
        mapping_data = {
            "version": "1.0",
            "mappings": [
                {
                    "id": 1,
                    "pattern": "店舗",
                    "match_type": MATCH_TYPE_CONTAINS,
                    "category": "テストカテゴリ",
                    "column": "C",
                    "priority": 3,
                    "note": None
                }
            ],
            "default": {"category": "支払額", "column": "B"}
        }

        records = [
            {'store': '登録店舗A', 'amount': 1000},
            {'store': '登録店舗B', 'amount': 2000},
            {'store': '登録店舗C', 'amount': 3000},
        ]

        # バッチ処理
        result_batch = determine_categories_batch(records, mapping_data)
        assert len(result_batch) == 3
        for record in result_batch:
            assert record['matched'] is True
            assert record['category'] == 'テストカテゴリ'
            assert record['column'] == 'C'

        # 未登録店舗検出（0件であることを確認）
        unregistered = detect_unregistered_stores(records, mapping_data)
        assert len(unregistered) == 0
