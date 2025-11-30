#!/usr/bin/env python3
"""
Phase 3: パターンマッチング機能の動作確認テスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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


def test_match_exact():
    """完全一致テスト"""
    print("=" * 60)
    print("テスト: match_exact() - 完全一致判定")
    print("=" * 60)

    tests = [
        ("ユニクロ", "ユニクロ", True),
        ("ユニクロ 池袋店", "ユニクロ", False),
        ("", "ユニクロ", False),
        ("ユニクロ", "", False),
    ]

    passed = 0
    for store, pattern, expected in tests:
        result = match_exact(store, pattern)
        status = "OK" if result == expected else "NG"
        if result == expected:
            passed += 1
        print(f"  [{status}] match_exact('{store}', '{pattern}') = {result} (期待値: {expected})")

    print(f"\n結果: {passed}/{len(tests)} 件成功\n")
    return passed == len(tests)


def test_match_startswith():
    """前方一致テスト"""
    print("=" * 60)
    print("テスト: match_startswith() - 前方一致判定")
    print("=" * 60)

    tests = [
        ("ユニクロ 池袋店", "ユニクロ", True),
        ("池袋ユニクロ", "ユニクロ", False),
        ("ユシンヤカマタテン", "ユシンヤ", True),
        ("", "ユニクロ", False),
    ]

    passed = 0
    for store, pattern, expected in tests:
        result = match_startswith(store, pattern)
        status = "OK" if result == expected else "NG"
        if result == expected:
            passed += 1
        print(f"  [{status}] match_startswith('{store}', '{pattern}') = {result} (期待値: {expected})")

    print(f"\n結果: {passed}/{len(tests)} 件成功\n")
    return passed == len(tests)


def test_match_contains():
    """部分一致テスト"""
    print("=" * 60)
    print("テスト: match_contains() - 部分一致判定")
    print("=" * 60)

    tests = [
        ("東京ユニクロ池袋店", "ユニクロ", True),
        ("ユシンヤカマタテン", "ユシンヤ", True),
        ("カマタユシンヤ", "ユシンヤ", True),
        ("無印良品", "ユニクロ", False),
        ("", "ユニクロ", False),
    ]

    passed = 0
    for store, pattern, expected in tests:
        result = match_contains(store, pattern)
        status = "OK" if result == expected else "NG"
        if result == expected:
            passed += 1
        print(f"  [{status}] match_contains('{store}', '{pattern}') = {result} (期待値: {expected})")

    print(f"\n結果: {passed}/{len(tests)} 件成功\n")
    return passed == len(tests)


def test_match_keyword():
    """キーワード一致テスト"""
    print("=" * 60)
    print("テスト: match_keyword() - キーワード一致判定")
    print("=" * 60)

    tests = [
        ("イオン幕張新都心", "イオン 幕張", True),
        ("イオンスタイル幕張新都心", "イオン 幕張", True),
        ("イオン池袋", "イオン 幕張", False),
        ("幕張イオン", "イオン 幕張", True),
        ("", "イオン 幕張", False),
    ]

    passed = 0
    for store, pattern, expected in tests:
        result = match_keyword(store, pattern)
        status = "OK" if result == expected else "NG"
        if result == expected:
            passed += 1
        print(f"  [{status}] match_keyword('{store}', '{pattern}') = {result} (期待値: {expected})")

    print(f"\n結果: {passed}/{len(tests)} 件成功\n")
    return passed == len(tests)


def test_execute_pattern_match():
    """パターンマッチング実行テスト"""
    print("=" * 60)
    print("テスト: execute_pattern_match() - パターンマッチング実行")
    print("=" * 60)

    # テストケース
    tests = [
        # (店舗名, エントリ, 期待値)
        ("ユニクロ", {'pattern': 'ユニクロ', 'match_type': MATCH_TYPE_EXACT}, True),
        ("ユニクロ池袋", {'pattern': 'ユニクロ', 'match_type': MATCH_TYPE_STARTSWITH}, True),
        ("東京ユニクロ池袋", {'pattern': 'ユニクロ', 'match_type': MATCH_TYPE_CONTAINS}, True),
        ("イオン幕張新都心", {'pattern': 'イオン 幕張', 'match_type': MATCH_TYPE_KEYWORD}, True),
        ("池袋店", {'pattern': 'ユニクロ', 'match_type': MATCH_TYPE_EXACT}, False),
    ]

    passed = 0
    for store, entry, expected in tests:
        result = execute_pattern_match(store, entry)
        status = "OK" if result == expected else "NG"
        if result == expected:
            passed += 1
        print(f"  [{status}] execute_pattern_match('{store}', pattern='{entry['pattern']}', type='{entry['match_type']}') = {result} (期待値: {expected})")

    # 不明なmatch_typeのテスト
    print("\n  [エラーハンドリングテスト]")
    try:
        invalid_entry = {'pattern': 'ユニクロ', 'match_type': 'unknown_type'}
        execute_pattern_match("ユニクロ", invalid_entry)
        print(f"  [NG] CategoryMatchErrorが発生しませんでした")
    except CategoryMatchError as e:
        print(f"  [OK] CategoryMatchErrorが正しく発生しました: {e.message}")
        passed += 1

    total_tests = len(tests) + 1
    print(f"\n結果: {passed}/{total_tests} 件成功\n")
    return passed == total_tests


def test_find_best_match():
    """最適マッチング選択テスト"""
    print("=" * 60)
    print("テスト: find_best_match() - 最適マッチング選択")
    print("=" * 60)

    # テストデータ: 複数のマッピングエントリ
    mappings: list[MappingEntry] = [
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

    tests = [
        # (店舗名, 期待されるカテゴリ, 期待されるmatch_type)
        ("ユニクロ", "衣類費(完全一致)", MATCH_TYPE_EXACT),  # 完全一致が最優先
        ("ユニクロ池袋店", "衣類費(前方一致)", MATCH_TYPE_STARTSWITH),  # 次に前方一致
        ("東京ユニクロ", "衣類費(部分一致)", MATCH_TYPE_CONTAINS),  # 部分一致のみ
        ("無印良品", None, None),  # マッチなし
    ]

    passed = 0
    for store, expected_category, expected_match_type in tests:
        result = find_best_match(store, mappings)
        if expected_category is None:
            status = "OK" if result is None else "NG"
            if result is None:
                passed += 1
            print(f"  [{status}] find_best_match('{store}') = None (期待値: None)")
        else:
            actual_category = result['category'] if result else None
            actual_match_type = result['match_type'] if result else None
            status = "OK" if (actual_category == expected_category and actual_match_type == expected_match_type) else "NG"
            if actual_category == expected_category and actual_match_type == expected_match_type:
                passed += 1
            print(f"  [{status}] find_best_match('{store}') = {actual_category} ({actual_match_type}) (期待値: {expected_category})")

    print(f"\n結果: {passed}/{len(tests)} 件成功\n")
    return passed == len(tests)


def main():
    """全テスト実行"""
    print("\n" + "=" * 60)
    print("Phase 3: パターンマッチング機能 - 動作確認テスト")
    print("=" * 60 + "\n")

    all_passed = True

    # 各テスト実行
    all_passed &= test_match_exact()
    all_passed &= test_match_startswith()
    all_passed &= test_match_contains()
    all_passed &= test_match_keyword()
    all_passed &= test_execute_pattern_match()
    all_passed &= test_find_best_match()

    # 最終結果
    print("=" * 60)
    if all_passed:
        print("すべてのテストが成功しました！")
    else:
        print("一部のテストが失敗しました。")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
