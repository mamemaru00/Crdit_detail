"""
Phase 3: パターンマッチング機能のテスト (pytest形式)

このモジュールは以下の関数のテストを実施します:
- match_exact(): 完全一致判定
- match_startswith(): 前方一致判定
- match_contains(): 部分一致判定
- match_keyword(): キーワード一致判定
- execute_pattern_match(): パターンマッチング実行
- find_best_match(): 最適マッチング選択
"""

import pytest
from modules.category_logic import (
    match_exact,
    match_startswith,
    match_contains,
    match_keyword,
    execute_pattern_match,
    find_best_match,
    MappingEntry,
    CategoryMatchError,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_STARTSWITH,
    MATCH_TYPE_CONTAINS,
    MATCH_TYPE_KEYWORD,
    PRIORITY_EXACT,
    PRIORITY_STARTSWITH,
    PRIORITY_CONTAINS,
    PRIORITY_KEYWORD
)


class TestMatchExact:
    """完全一致判定のテスト"""

    @pytest.mark.parametrize("store,pattern,expected", [
        ("ユニクロ", "ユニクロ", True),
        ("ユニクロ 池袋店", "ユニクロ", False),
        ("", "ユニクロ", False),
        ("ユニクロ", "", False),
    ])
    def test_match_exact(self, store, pattern, expected):
        """完全一致判定のパラメータ化テスト"""
        result = match_exact(store, pattern)
        assert result == expected


class TestMatchStartswith:
    """前方一致判定のテスト"""

    @pytest.mark.parametrize("store,pattern,expected", [
        ("ユニクロ 池袋店", "ユニクロ", True),
        ("池袋ユニクロ", "ユニクロ", False),
        ("ユシンヤカマタテン", "ユシンヤ", True),
        ("", "ユニクロ", False),
    ])
    def test_match_startswith(self, store, pattern, expected):
        """前方一致判定のパラメータ化テスト"""
        result = match_startswith(store, pattern)
        assert result == expected


class TestMatchContains:
    """部分一致判定のテスト"""

    @pytest.mark.parametrize("store,pattern,expected", [
        ("東京ユニクロ池袋店", "ユニクロ", True),
        ("ユシンヤカマタテン", "ユシンヤ", True),
        ("カマタユシンヤ", "ユシンヤ", True),
        ("無印良品", "ユニクロ", False),
        ("", "ユニクロ", False),
    ])
    def test_match_contains(self, store, pattern, expected):
        """部分一致判定のパラメータ化テスト"""
        result = match_contains(store, pattern)
        assert result == expected


class TestMatchKeyword:
    """キーワード一致判定のテスト"""

    @pytest.mark.parametrize("store,pattern,expected", [
        ("イオン幕張新都心", "イオン 幕張", True),
        ("イオンスタイル幕張新都心", "イオン 幕張", True),
        ("イオン池袋", "イオン 幕張", False),
        ("幕張イオン", "イオン 幕張", True),
        ("", "イオン 幕張", False),
    ])
    def test_match_keyword(self, store, pattern, expected):
        """キーワード一致判定のパラメータ化テスト"""
        result = match_keyword(store, pattern)
        assert result == expected


class TestExecutePatternMatch:
    """パターンマッチング実行のテスト"""

    @pytest.mark.parametrize("store,entry,expected", [
        ("ユニクロ", {'pattern': 'ユニクロ', 'match_type': MATCH_TYPE_EXACT}, True),
        ("ユニクロ池袋", {'pattern': 'ユニクロ', 'match_type': MATCH_TYPE_STARTSWITH}, True),
        ("東京ユニクロ池袋", {'pattern': 'ユニクロ', 'match_type': MATCH_TYPE_CONTAINS}, True),
        ("イオン幕張新都心", {'pattern': 'イオン 幕張', 'match_type': MATCH_TYPE_KEYWORD}, True),
        ("池袋店", {'pattern': 'ユニクロ', 'match_type': MATCH_TYPE_EXACT}, False),
    ])
    def test_execute_pattern_match(self, store, entry, expected):
        """パターンマッチング実行のパラメータ化テスト"""
        result = execute_pattern_match(store, entry)
        assert result == expected

    def test_execute_pattern_match_invalid_type(self):
        """不明なmatch_typeの場合にCategoryMatchErrorが発生"""
        invalid_entry = {'pattern': 'ユニクロ', 'match_type': 'unknown_type'}
        with pytest.raises(CategoryMatchError) as exc_info:
            execute_pattern_match("ユニクロ", invalid_entry)

        assert '不明なmatch_typeです' in exc_info.value.message


class TestFindBestMatch:
    """最適マッチング選択のテスト"""

    @pytest.fixture
    def mappings(self) -> list:
        """テスト用のマッピングエントリフィクスチャ"""
        return [
            {
                'id': 1,
                'pattern': 'ユニクロ',
                'match_type': MATCH_TYPE_CONTAINS,
                'category': '衣類費(部分一致)',
                'column': 'D',
                'priority': PRIORITY_CONTAINS,
                'note': None
            },
            {
                'id': 2,
                'pattern': 'ユニクロ',
                'match_type': MATCH_TYPE_EXACT,
                'category': '衣類費(完全一致)',
                'column': 'C',
                'priority': PRIORITY_EXACT,
                'note': None
            },
            {
                'id': 3,
                'pattern': 'ユニ',
                'match_type': MATCH_TYPE_STARTSWITH,
                'category': '衣類費(前方一致)',
                'column': 'E',
                'priority': PRIORITY_STARTSWITH,
                'note': None
            },
        ]

    def test_find_best_match_exact(self, mappings):
        """完全一致が最優先されることを確認"""
        result = find_best_match("ユニクロ", mappings)
        assert result is not None
        assert result['category'] == '衣類費(完全一致)'
        assert result['match_type'] == MATCH_TYPE_EXACT

    def test_find_best_match_startswith(self, mappings):
        """前方一致が次点として選択されることを確認"""
        result = find_best_match("ユニクロ池袋店", mappings)
        assert result is not None
        assert result['category'] == '衣類費(前方一致)'
        assert result['match_type'] == MATCH_TYPE_STARTSWITH

    def test_find_best_match_contains(self, mappings):
        """部分一致のみマッチする場合を確認"""
        result = find_best_match("東京ユニクロ", mappings)
        assert result is not None
        assert result['category'] == '衣類費(部分一致)'
        assert result['match_type'] == MATCH_TYPE_CONTAINS

    def test_find_best_match_none(self, mappings):
        """マッチしない場合はNoneを返すことを確認"""
        result = find_best_match("無印良品", mappings)
        assert result is None
