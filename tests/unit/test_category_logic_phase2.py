"""
Phase 2: マッピングデータ読込・検証機能のテスト (pytest形式)

このモジュールは以下のテストケースを実行します:
1. 正常系: data/mapping.jsonの読み込み・検証成功
2. 異常系1: ファイルが存在しない場合にMappingLoadError
3. 異常系2: JSONが不正な場合にInvalidMappingFormatError
4. 異常系3: 必須フィールドが不足している場合にMappingValidationError
5. 異常系4: match_typeが不正な場合にMappingValidationError
6. 異常系5: columnが不正な場合にMappingValidationError
7. 異常系6: priorityが範囲外の場合にMappingValidationError
"""

import json
import tempfile
import pytest
from pathlib import Path

from modules.category_logic import (
    load_mapping_data,
    validate_mapping_entry,
    validate_mapping_data,
    MappingLoadError,
    MappingValidationError,
    InvalidMappingFormatError
)


def test_normal_case():
    """正常系: data/mapping.jsonの読み込み・検証成功"""
    # マッピングデータ読み込み
    data = load_mapping_data('data/mapping.json')

    assert 'version' in data
    assert 'mappings' in data
    assert 'default' in data
    assert isinstance(data['mappings'], list)
    assert len(data['mappings']) > 0

    # データ全体を検証（例外が発生しないことを確認）
    validate_mapping_data(data)

    # デフォルト設定の確認
    assert data['default']['category'] == '支払額'
    assert data['default']['column'] == 'B'


def test_file_not_found():
    """異常系: ファイルが存在しない場合にMappingLoadError"""
    with pytest.raises(MappingLoadError) as exc_info:
        load_mapping_data('config/non_existent_file.json')

    assert 'マッピングファイルが見つかりません' in exc_info.value.message
    assert 'path' in exc_info.value.details


def test_invalid_json():
    """異常系: JSONが不正な場合にInvalidMappingFormatError"""
    # 一時ファイル作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{ invalid json content }")
        temp_file = f.name

    try:
        with pytest.raises(InvalidMappingFormatError) as exc_info:
            load_mapping_data(temp_file)

        assert 'JSONファイルの解析に失敗しました' in exc_info.value.message
    finally:
        # 一時ファイル削除
        Path(temp_file).unlink(missing_ok=True)


def test_missing_fields():
    """異常系: 必須フィールドが不足している場合にMappingValidationError"""
    # versionフィールドが不足しているデータ
    invalid_data = {
        "mappings": [
            {
                "id": 1,
                "pattern": "テスト",
                "match_type": "exact",
                "category": "テストカテゴリ",
                "column": "C",
                "priority": 1
            }
        ],
        "default": {
            "category": "支払額",
            "column": "B"
        }
    }

    # 一時ファイル作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_data, f, ensure_ascii=False, indent=2)
        temp_file = f.name

    try:
        with pytest.raises(MappingValidationError) as exc_info:
            load_mapping_data(temp_file)

        assert '必須フィールドが不足しています' in exc_info.value.message
        assert 'version' in exc_info.value.message
    finally:
        # 一時ファイル削除
        Path(temp_file).unlink(missing_ok=True)


def test_invalid_match_type():
    """異常系: match_typeが不正な場合にMappingValidationError"""
    # 不正なmatch_typeを持つエントリ
    invalid_entry = {
        "id": 1,
        "pattern": "テスト",
        "match_type": "invalid_type",  # 不正な値
        "category": "テストカテゴリ",
        "column": "C",
        "priority": 1
    }

    with pytest.raises(MappingValidationError) as exc_info:
        validate_mapping_entry(invalid_entry)

    assert 'match_typeが不正です' in exc_info.value.message
    assert 'invalid_type' in exc_info.value.message


def test_invalid_column():
    """異常系: columnが不正な場合にMappingValidationError"""
    # 不正なcolumnを持つエントリ
    invalid_entry = {
        "id": 1,
        "pattern": "テスト",
        "match_type": "exact",
        "category": "テストカテゴリ",
        "column": "Z",  # 不正な値（有効範囲はB～V）
        "priority": 1
    }

    with pytest.raises(MappingValidationError) as exc_info:
        validate_mapping_entry(invalid_entry)

    assert 'columnが不正です' in exc_info.value.message


def test_invalid_priority():
    """異常系: priorityが範囲外の場合にMappingValidationError"""
    # 不正なpriorityを持つエントリ
    invalid_entry = {
        "id": 1,
        "pattern": "テスト",
        "match_type": "exact",
        "category": "テストカテゴリ",
        "column": "C",
        "priority": 5  # 不正な値（有効範囲は1～4）
    }

    with pytest.raises(MappingValidationError) as exc_info:
        validate_mapping_entry(invalid_entry)

    assert 'priorityは1～4の整数である必要があります' in exc_info.value.message
