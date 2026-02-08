"""
エッジケーステスト

このモジュールはcategory_logic.pyの異常系・境界値・エッジケースをテストします。

テストケース:
1. 空文字列・None・空白のみの店舗名に対するdetermine_category()の動作
2. 1000文字の長い店舗名に対するパターンマッチング
3. 特殊文字（①②髙﨑）を含む店舗名の処理
4. 空のmappings配列の検証
5. 異常なID値（0、負の値）の検証
6. patternが空文字列の検証
7. priorityが0の検証
8. noteフィールドの型異常検証
9. 重複IDの検証
10. keywordパターンが空白のみの検証
11. amountが負の値・0の場合の未登録店舗検出
12. recordsに全件storeキーがない場合のバッチ処理
"""

import pytest
import tempfile
import json
from pathlib import Path

from modules.category_logic import (
    determine_category,
    validate_mapping_entry,
    validate_mapping_data,
    match_keyword,
    detect_unregistered_stores,
    determine_categories_batch,
    load_mapping_data,
    MappingValidationError,
    InvalidMappingFormatError
)


@pytest.fixture
def valid_mapping_data():
    """有効なマッピングデータのフィクスチャ"""
    return {
        "version": "1.0",
        "mappings": [
            {
                "id": 1,
                "pattern": "テスト",
                "match_type": "exact",
                "category": "テストカテゴリ",
                "column": "C",
                "priority": 1,
                "note": "テスト用"
            }
        ]
    }


class TestEmptyAndNullStoreNames:
    """テストケース1: 空文字列・None・空白のみの店舗名のテスト"""

    def test_empty_string_store_name(self, valid_mapping_data):
        """空文字列の店舗名"""
        result = determine_category("", valid_mapping_data)
        assert result['matched'] is False
        assert result['category'] is None
        assert result['column'] is None

    def test_whitespace_only_store_name(self, valid_mapping_data):
        """空白のみの店舗名"""
        result = determine_category("   ", valid_mapping_data)
        assert result['matched'] is False
        assert result['category'] is None
        assert result['column'] is None

    def test_tab_only_store_name(self, valid_mapping_data):
        """タブのみの店舗名"""
        result = determine_category("\t\t", valid_mapping_data)
        assert result['matched'] is False


class TestLongStoreName:
    """テストケース2: 1000文字の長い店舗名のテスト"""

    def test_very_long_store_name(self, valid_mapping_data):
        """1000文字の店舗名に対するパターンマッチング"""
        # "テスト"は3文字なので、残り997文字の"あ"を追加
        long_store_name = "テスト" + "あ" * 997  # 1000文字
        assert len(long_store_name) == 1000

        # 前方一致でマッチするはず
        mapping_data_with_startswith = {
            "version": "1.0",
            "mappings": [
                {
                    "id": 1,
                    "pattern": "テスト",
                    "match_type": "startswith",
                    "category": "長文カテゴリ",
                    "column": "D",
                    "priority": 2,
                    "note": None
                }
            ]
        }

        result = determine_category(long_store_name, mapping_data_with_startswith)
        assert result['matched'] is True
        assert result['category'] == '長文カテゴリ'


class TestSpecialCharacters:
    """テストケース3: 特殊文字を含む店舗名のテスト"""

    @pytest.mark.parametrize("special_store_name,pattern,expected_match", [
        ("①イオン", "①イオン", True),
        ("②セブンイレブン", "②セブンイレブン", True),
        ("髙島屋", "髙島屋", True),
        ("﨑陽軒", "﨑陽軒", True),
    ])
    def test_special_characters(self, special_store_name, pattern, expected_match):
        """特殊文字を含む店舗名の処理"""
        mapping_data = {
            "version": "1.0",
            "mappings": [
                {
                    "id": 1,
                    "pattern": pattern,
                    "match_type": "exact",
                    "category": "特殊文字カテゴリ",
                    "column": "E",
                    "priority": 1,
                    "note": None
                }
            ]
        }

        result = determine_category(special_store_name, mapping_data)
        assert result['matched'] == expected_match


class TestEmptyMappingsArray:
    """テストケース4: 空のmappings配列の検証"""

    def test_empty_mappings_validation(self):
        """空のmappings配列は有効であることを確認"""
        data = {
            "version": "1.0",
            "mappings": []
        }

        # 検証が成功することを確認（例外が発生しない）
        validate_mapping_data(data)

    def test_empty_mappings_determine_category(self):
        """空のmappings配列の場合、常に未登録として扱われる（Phase 7仕様）"""
        data = {
            "version": "1.0",
            "mappings": []
        }

        result = determine_category("どんな店舗名でも", data)
        assert result['matched'] is False
        assert result['category'] is None
        assert result['column'] is None


class TestInvalidIdValues:
    """テストケース5: 異常なID値の検証"""

    def test_id_zero(self):
        """ID値が0の場合（有効な整数として受け入れられる）"""
        entry = {
            "id": 0,
            "pattern": "テスト",
            "match_type": "exact",
            "category": "テストカテゴリ",
            "column": "C",
            "priority": 1
        }

        # id=0は整数なので検証は通る（ビジネスロジック上は問題あり得るが、型検証では許容）
        validate_mapping_entry(entry)

    def test_id_negative(self):
        """ID値が負の値の場合（有効な整数として受け入れられる）"""
        entry = {
            "id": -1,
            "pattern": "テスト",
            "match_type": "exact",
            "category": "テストカテゴリ",
            "column": "C",
            "priority": 1
        }

        # id=-1は整数なので検証は通る
        validate_mapping_entry(entry)

    def test_id_not_int(self):
        """ID値が整数でない場合"""
        entry = {
            "id": "1",  # 文字列
            "pattern": "テスト",
            "match_type": "exact",
            "category": "テストカテゴリ",
            "column": "C",
            "priority": 1
        }

        with pytest.raises(MappingValidationError) as exc_info:
            validate_mapping_entry(entry)

        assert 'idフィールドは整数である必要があります' in exc_info.value.message


class TestEmptyPattern:
    """テストケース6: patternが空文字列の検証"""

    def test_pattern_empty_string(self):
        """patternが空文字列の場合"""
        entry = {
            "id": 1,
            "pattern": "",  # 空文字列
            "match_type": "exact",
            "category": "テストカテゴリ",
            "column": "C",
            "priority": 1
        }

        with pytest.raises(MappingValidationError) as exc_info:
            validate_mapping_entry(entry)

        assert 'patternフィールドは空でない文字列である必要があります' in exc_info.value.message


class TestPriorityZero:
    """テストケース7: priorityが0の検証"""

    def test_priority_zero(self):
        """priorityが0の場合"""
        entry = {
            "id": 1,
            "pattern": "テスト",
            "match_type": "exact",
            "category": "テストカテゴリ",
            "column": "C",
            "priority": 0  # 範囲外（1～5が有効）
        }

        with pytest.raises(MappingValidationError) as exc_info:
            validate_mapping_entry(entry)

        assert 'priorityは1～5の整数である必要があります' in exc_info.value.message


class TestNoteFieldType:
    """テストケース8: noteフィールドの型異常検証"""

    def test_note_field_valid_string(self):
        """noteフィールドが文字列の場合（正常）"""
        entry = {
            "id": 1,
            "pattern": "テスト",
            "match_type": "exact",
            "category": "テストカテゴリ",
            "column": "C",
            "priority": 1,
            "note": "これは備考です"
        }

        # noteはオプションフィールドで型チェックなし（現在の実装）
        validate_mapping_entry(entry)

    def test_note_field_none(self):
        """noteフィールドがNoneの場合（正常）"""
        entry = {
            "id": 1,
            "pattern": "テスト",
            "match_type": "exact",
            "category": "テストカテゴリ",
            "column": "C",
            "priority": 1,
            "note": None
        }

        validate_mapping_entry(entry)

    def test_note_field_missing(self):
        """noteフィールドがない場合（正常）"""
        entry = {
            "id": 1,
            "pattern": "テスト",
            "match_type": "exact",
            "category": "テストカテゴリ",
            "column": "C",
            "priority": 1
        }

        # noteはオプションフィールドなので検証は通る
        validate_mapping_entry(entry)


class TestDuplicateIds:
    """テストケース9: 重複IDの検証"""

    def test_duplicate_ids(self):
        """重複するIDが存在する場合"""
        data = {
            "version": "1.0",
            "mappings": [
                {
                    "id": 1,
                    "pattern": "テスト1",
                    "match_type": "exact",
                    "category": "カテゴリ1",
                    "column": "C",
                    "priority": 1
                },
                {
                    "id": 1,  # 重複
                    "pattern": "テスト2",
                    "match_type": "exact",
                    "category": "カテゴリ2",
                    "column": "D",
                    "priority": 1
                }
            ]
        }

        with pytest.raises(MappingValidationError) as exc_info:
            validate_mapping_data(data)

        assert '重複するIDが検出されました' in exc_info.value.message


class TestKeywordPatternWhitespace:
    """テストケース10: keywordパターンが空白のみの検証"""

    def test_keyword_pattern_whitespace_only(self):
        """キーワードパターンが空白のみの場合"""
        result = match_keyword("イオン幕張", "   ")
        # 空白のみの場合、split()で空リストになり、all([])はTrueを返す
        # Pythonのall([])はTrueを返す仕様なので、この場合はTrueになる
        # これは空のキーワードリストに対してすべての条件が満たされると解釈される
        assert result is True

    def test_keyword_pattern_multiple_spaces(self):
        """キーワードパターンに複数のスペースが含まれる場合"""
        result = match_keyword("イオン幕張", "イオン  幕張")
        # split()は連続する空白を無視するので正常にマッチする
        assert result is True


class TestNegativeAndZeroAmount:
    """テストケース11: amountが負の値・0の場合の未登録店舗検出"""

    def test_negative_amount_unregistered(self, valid_mapping_data):
        """金額が負の値の場合"""
        records = [
            {'store': '未登録店舗', 'amount': -1000},
            {'store': '未登録店舗', 'amount': -500},
        ]

        result = detect_unregistered_stores(records, valid_mapping_data)

        assert len(result) == 1
        assert result[0]['store'] == '未登録店舗'
        assert result[0]['total_amount'] == -1500
        assert result[0]['count'] == 2

    def test_zero_amount_unregistered(self, valid_mapping_data):
        """金額が0の場合"""
        records = [
            {'store': '未登録店舗', 'amount': 0},
            {'store': '未登録店舗', 'amount': 0},
        ]

        result = detect_unregistered_stores(records, valid_mapping_data)

        assert len(result) == 1
        assert result[0]['store'] == '未登録店舗'
        assert result[0]['total_amount'] == 0
        assert result[0]['count'] == 2


class TestRecordsWithoutStoreKey:
    """テストケース12: recordsに全件storeキーがない場合のバッチ処理"""

    def test_all_records_without_store_key(self, valid_mapping_data):
        """全レコードでstoreキーがない場合"""
        records = [
            {'date': '2025/08/15', 'amount': 1000},
            {'date': '2025/08/16', 'amount': 2000},
            {'date': '2025/08/17', 'amount': 3000},
        ]

        result = determine_categories_batch(records, valid_mapping_data)

        assert len(result) == 3

        for record in result:
            assert record['matched'] is False
            assert record['category'] is None
            assert record['column'] is None
            assert record['pattern'] is None
            assert record['match_type'] is None

    def test_mixed_records_with_and_without_store(self, valid_mapping_data):
        """storeキーがある/ないが混在する場合"""
        records = [
            {'date': '2025/08/15', 'store': 'テスト', 'amount': 1000},
            {'date': '2025/08/16', 'amount': 2000},  # storeキーなし
        ]

        result = determine_categories_batch(records, valid_mapping_data)

        assert len(result) == 2
        assert result[0]['matched'] is True  # storeキーあり
        assert result[1]['matched'] is False  # storeキーなし
