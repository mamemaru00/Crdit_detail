"""
マッピング管理モジュール(mapping_manager.py)のテストスイート

このテストスイートは以下のカテゴリをカバーします:
1. CRUD操作テスト（10ケース）
2. バリデーションテスト（4ケース）
3. ファイルI/Oテスト（4ケース）
4. ID管理テスト（3ケース）
5. 検索機能テスト（3ケース）

合計: 24テストケース
カバレッジ目標: 80%以上
"""

import json
import tempfile
import pytest
import shutil
from pathlib import Path
from unittest import mock

from modules.mapping_manager import (
    get_all_mappings,
    get_mapping_by_id,
    add_mapping,
    update_mapping,
    delete_mapping,
    get_next_id,
    MappingNotFoundError,
    DuplicateMappingError,
    MappingSaveError,
    _check_duplicate,
    _save_mapping_data,
    _create_backup
)
from modules.category_logic import (
    MappingValidationError,
    DEFAULT_MAPPING_PATH
)


# ==================== フィクスチャ ====================

@pytest.fixture
def temp_mapping_file(tmp_path):
    """
    一時的なマッピングファイルを作成するフィクスチャ

    Returns:
        Path: 一時マッピングファイルのパス
    """
    mapping_file = tmp_path / "mapping.json"
    data = {
        "version": "1.0",
        "mappings": [
            {
                "id": 1,
                "pattern": "テスト店舗A",
                "match_type": "contains",
                "category": "外食費",
                "column": "C",
                "priority": 1
            },
            {
                "id": 2,
                "pattern": "テスト店舗B",
                "match_type": "startswith",
                "category": "日用品費",
                "column": "D",
                "priority": 2
            }
        ],
        "default": {
            "category": "支払額",
            "column": "B"
        }
    }
    with mapping_file.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return mapping_file


@pytest.fixture
def empty_mapping_file(tmp_path):
    """
    空のマッピングファイルを作成するフィクスチャ

    Returns:
        Path: 空の一時マッピングファイルのパス
    """
    mapping_file = tmp_path / "mapping_empty.json"
    data = {
        "version": "1.0",
        "mappings": [],
        "default": {
            "category": "支払額",
            "column": "B"
        }
    }
    with mapping_file.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return mapping_file


@pytest.fixture
def sample_mapping_data():
    """
    テスト用のサンプルマッピングデータ

    Returns:
        dict: サンプルマッピングデータ
    """
    return {
        "version": "1.0",
        "mappings": [
            {
                "id": 1,
                "pattern": "ユニクロ",
                "match_type": "contains",
                "category": "衣服費",
                "column": "E",
                "priority": 1
            },
            {
                "id": 2,
                "pattern": "セブンイレブン",
                "match_type": "startswith",
                "category": "外食費",
                "column": "C",
                "priority": 1
            },
            {
                "id": 3,
                "pattern": "AMAZON",
                "match_type": "exact",
                "category": "書籍費",
                "column": "M",
                "priority": 1
            }
        ],
        "default": {
            "category": "支払額",
            "column": "B"
        }
    }


# ==================== CRUD操作テスト（10ケース） ====================

def test_get_all_mappings_empty(empty_mapping_file):
    """
    空の状態での全件取得
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(empty_mapping_file)):
        mappings = get_all_mappings()
        assert isinstance(mappings, list)
        assert len(mappings) == 0


def test_get_all_mappings_with_data(temp_mapping_file):
    """
    データがある状態での全件取得
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        mappings = get_all_mappings()
        assert isinstance(mappings, list)
        assert len(mappings) == 2
        assert mappings[0]['pattern'] == 'テスト店舗A'
        assert mappings[1]['pattern'] == 'テスト店舗B'


def test_add_mapping_success(temp_mapping_file):
    """
    正常なマッピング追加
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        new_entry = {
            'pattern': 'ローソン',
            'match_type': 'startswith',
            'category': '外食費',
            'column': 'C',
            'priority': 1
        }

        result = add_mapping(new_entry)

        # 追加されたエントリの検証
        assert result['id'] == 3  # 次のIDは3
        assert result['pattern'] == 'ローソン'
        assert result['category'] == '外食費'

        # ファイルに保存されたか確認
        mappings = get_all_mappings()
        assert len(mappings) == 3


def test_add_mapping_auto_id(empty_mapping_file):
    """
    ID自動生成の確認
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(empty_mapping_file)):
        new_entry = {
            'pattern': 'テスト',
            'match_type': 'exact',
            'category': 'テストカテゴリ',
            'column': 'C',
            'priority': 1
        }

        result = add_mapping(new_entry)

        # 最初のIDは1
        assert result['id'] == 1


def test_update_mapping_success(temp_mapping_file):
    """
    正常な更新（完全更新）
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        update_data = {
            'pattern': 'テスト店舗A更新',
            'match_type': 'exact',
            'category': '交通費',
            'column': 'F',
            'priority': 2
        }

        result = update_mapping(1, update_data)

        # 更新後の値を確認
        assert result['id'] == 1
        assert result['pattern'] == 'テスト店舗A更新'
        assert result['match_type'] == 'exact'
        assert result['category'] == '交通費'
        assert result['column'] == 'F'
        assert result['priority'] == 2


def test_update_mapping_partial(temp_mapping_file):
    """
    部分更新（PATCHパターン）
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        # priorityのみ更新
        update_data = {'priority': 3}

        result = update_mapping(1, update_data)

        # priorityのみ変更され、他は元のまま
        assert result['id'] == 1
        assert result['pattern'] == 'テスト店舗A'  # 変更なし
        assert result['match_type'] == 'contains'  # 変更なし
        assert result['priority'] == 3  # 変更


def test_delete_mapping_success(temp_mapping_file):
    """
    正常な削除
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        result = delete_mapping(1)

        assert result is True

        # 削除されたか確認
        mappings = get_all_mappings()
        assert len(mappings) == 1
        assert mappings[0]['id'] == 2


def test_delete_mapping_not_found(temp_mapping_file):
    """
    存在しないID削除時のエラー
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        with pytest.raises(MappingNotFoundError) as exc_info:
            delete_mapping(999)

        assert 'ID 999 のマッピングが見つかりません' in exc_info.value.message
        assert exc_info.value.details['mapping_id'] == 999


def test_get_mapping_by_id_success(temp_mapping_file):
    """
    ID指定取得成功
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        mapping = get_mapping_by_id(1)

        assert mapping is not None
        assert mapping['id'] == 1
        assert mapping['pattern'] == 'テスト店舗A'


def test_get_mapping_by_id_not_found(temp_mapping_file):
    """
    存在しないID取得時のエラー
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        mapping = get_mapping_by_id(999)

        assert mapping is None


# ==================== バリデーションテスト（4ケース） ====================

def test_add_mapping_duplicate_error(temp_mapping_file):
    """
    重複エラー（pattern + match_type）
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        # 既に存在するpattern + match_typeの組み合わせ
        duplicate_entry = {
            'pattern': 'テスト店舗A',
            'match_type': 'contains',
            'category': '別カテゴリ',
            'column': 'E',
            'priority': 1
        }

        with pytest.raises(DuplicateMappingError) as exc_info:
            add_mapping(duplicate_entry)

        assert '同じpatternとmatch_typeの組み合わせが既に存在します' in exc_info.value.message
        assert exc_info.value.details['pattern'] == 'テスト店舗A'
        assert exc_info.value.details['match_type'] == 'contains'


def test_add_mapping_invalid_match_type(temp_mapping_file):
    """
    無効なmatch_type
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        invalid_entry = {
            'pattern': 'テスト',
            'match_type': 'invalid_type',  # 無効な値
            'category': 'カテゴリ',
            'column': 'C',
            'priority': 1
        }

        with pytest.raises(MappingValidationError) as exc_info:
            add_mapping(invalid_entry)

        assert 'match_typeが不正です' in exc_info.value.message


def test_add_mapping_invalid_column(temp_mapping_file):
    """
    無効なcolumn
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        invalid_entry = {
            'pattern': 'テスト',
            'match_type': 'exact',
            'category': 'カテゴリ',
            'column': 'Z',  # 無効な列（C～Vの範囲外）
            'priority': 1
        }

        with pytest.raises(MappingValidationError) as exc_info:
            add_mapping(invalid_entry)

        assert 'columnが不正です' in exc_info.value.message


def test_update_mapping_invalid_data(temp_mapping_file):
    """
    更新時の無効データ
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        invalid_update = {
            'priority': 999  # 無効な優先順位（1～4の範囲外）
        }

        with pytest.raises(MappingValidationError) as exc_info:
            update_mapping(1, invalid_update)

        assert 'priorityは1～4の整数である必要があります' in exc_info.value.message


# ==================== ファイルI/Oテスト（4ケース） ====================

def test_save_and_load_mapping(temp_mapping_file, sample_mapping_data):
    """
    保存→読み込みの整合性
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        # データを保存
        _save_mapping_data(sample_mapping_data)

        # 再読み込み
        mappings = get_all_mappings()

        # 整合性確認
        assert len(mappings) == 3
        assert mappings[0]['pattern'] == 'ユニクロ'
        assert mappings[1]['pattern'] == 'セブンイレブン'
        assert mappings[2]['pattern'] == 'AMAZON'


def test_backup_creation(temp_mapping_file):
    """
    バックアップファイル作成確認
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        backup_dir = temp_mapping_file.parent / 'backups'
        backup_dir.mkdir(exist_ok=True)

        # バックアップ作成
        _create_backup(temp_mapping_file)

        # バックアップファイルが作成されたか確認
        backups = list(backup_dir.glob('mapping_*.json'))
        assert len(backups) >= 1


def test_backup_rotation(tmp_path):
    """
    バックアップ10件保持ルール
    """
    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text('{"version": "2.0", "mappings": []}')

    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir(exist_ok=True)

    # 15個のバックアップを作成
    for i in range(15):
        backup_file = backup_dir / f"mapping_2025010{i:02d}_120000.json"
        backup_file.write_text('{}')

    # 新しいバックアップ作成（古いものを削除）
    _create_backup(mapping_file)

    # 最新10件のみ保持されているか確認
    backups = sorted(backup_dir.glob('mapping_*.json'))
    assert len(backups) <= 11  # 新規1件 + 既存10件（古いものは削除）


def test_atomic_save(temp_mapping_file, sample_mapping_data):
    """
    アトミック保存（一時ファイル→replace）
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        # 一時ファイルパス
        temp_path = Path(str(temp_mapping_file) + '.tmp')

        # 保存実行
        _save_mapping_data(sample_mapping_data)

        # 一時ファイルは削除されているはず
        assert not temp_path.exists()

        # 本ファイルは存在する
        assert temp_mapping_file.exists()

        # データが正しく保存されているか確認
        with temp_mapping_file.open('r', encoding='utf-8') as f:
            loaded_data = json.load(f)

        assert len(loaded_data['mappings']) == 3


# ==================== ID管理テスト（3ケース） ====================

def test_get_next_id_sequential(temp_mapping_file):
    """
    ID連番生成
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        # 現在の最大IDは2
        next_id = get_next_id()
        assert next_id == 3

        # 新規追加
        new_entry = {
            'pattern': 'テスト',
            'match_type': 'exact',
            'category': 'カテゴリ',
            'column': 'C',
            'priority': 1
        }
        result = add_mapping(new_entry)
        assert result['id'] == 3

        # さらに次のID
        next_id = get_next_id()
        assert next_id == 4


def test_get_next_id_after_delete(temp_mapping_file):
    """
    削除後のID生成（再利用しない）
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        # ID=1を削除
        delete_mapping(1)

        # 次のIDは2ではなく3（再利用しない）
        next_id = get_next_id()
        assert next_id == 3


def test_id_uniqueness(temp_mapping_file):
    """
    ID一意性保証
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        # 複数のマッピングを追加
        for i in range(5):
            new_entry = {
                'pattern': f'テスト{i}',
                'match_type': 'exact',
                'category': 'カテゴリ',
                'column': 'C',
                'priority': 1
            }
            add_mapping(new_entry)

        # すべてのIDが一意であることを確認
        mappings = get_all_mappings()
        ids = [m['id'] for m in mappings]
        assert len(ids) == len(set(ids))  # 重複なし


# ==================== 検索機能テスト（3ケース） ====================

def test_search_mappings_by_pattern(temp_mapping_file):
    """
    パターン検索
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        mappings = get_all_mappings()

        # 'テスト店舗A'を含むエントリを検索
        result = [m for m in mappings if 'テスト店舗A' in m['pattern']]

        assert len(result) == 1
        assert result[0]['pattern'] == 'テスト店舗A'


def test_search_mappings_by_category(temp_mapping_file):
    """
    カテゴリ検索
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        mappings = get_all_mappings()

        # '外食費'カテゴリのエントリを検索
        result = [m for m in mappings if m['category'] == '外食費']

        assert len(result) == 1
        assert result[0]['category'] == '外食費'


def test_search_mappings_no_match(temp_mapping_file):
    """
    検索結果0件
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        mappings = get_all_mappings()

        # 存在しないパターンで検索
        result = [m for m in mappings if '存在しない店舗' in m['pattern']]

        assert len(result) == 0


# ==================== エラーハンドリングテスト ====================

def test_check_duplicate_function(sample_mapping_data):
    """
    _check_duplicate関数の直接テスト
    """
    existing_mappings = sample_mapping_data['mappings']

    # 重複するエントリ
    duplicate_entry = {
        'pattern': 'ユニクロ',
        'match_type': 'contains',
        'category': '別カテゴリ',
        'column': 'F',
        'priority': 2
    }

    # 重複エラーが発生することを確認
    with pytest.raises(DuplicateMappingError) as exc_info:
        _check_duplicate(duplicate_entry, existing_mappings)

    assert 'ユニクロ' in str(exc_info.value)


def test_update_mapping_not_found(temp_mapping_file):
    """
    更新対象が存在しない場合のエラー
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(temp_mapping_file)):
        with pytest.raises(MappingNotFoundError) as exc_info:
            update_mapping(999, {'priority': 1})

        assert 'ID 999 のマッピングが見つかりません' in exc_info.value.message


# ==================== カバレッジ向上用テスト ====================

def test_empty_pattern_add(empty_mapping_file):
    """
    空のpatternで追加エラー
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(empty_mapping_file)):
        invalid_entry = {
            'pattern': '',  # 空文字列
            'match_type': 'exact',
            'category': 'カテゴリ',
            'column': 'C',
            'priority': 1
        }

        with pytest.raises(MappingValidationError):
            add_mapping(invalid_entry)


def test_missing_required_field(empty_mapping_file):
    """
    必須フィールド不足エラー
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(empty_mapping_file)):
        invalid_entry = {
            'pattern': 'テスト',
            # match_typeが不足
            'category': 'カテゴリ',
            'column': 'C',
            'priority': 1
        }

        with pytest.raises(MappingValidationError):
            add_mapping(invalid_entry)


# ==================== 統合テスト ====================

def test_full_crud_cycle(empty_mapping_file):
    """
    完全なCRUDサイクルテスト
    """
    with mock.patch('modules.mapping_manager.DEFAULT_MAPPING_PATH', str(empty_mapping_file)):
        # 1. Create - 3つのマッピングを追加
        entries = [
            {'pattern': '店舗A', 'match_type': 'exact', 'category': 'カテゴリA', 'column': 'C', 'priority': 1},
            {'pattern': '店舗B', 'match_type': 'startswith', 'category': 'カテゴリB', 'column': 'D', 'priority': 2},
            {'pattern': '店舗C', 'match_type': 'contains', 'category': 'カテゴリC', 'column': 'E', 'priority': 3}
        ]

        for entry in entries:
            add_mapping(entry)

        # 2. Read - 全件取得
        mappings = get_all_mappings()
        assert len(mappings) == 3

        # 3. Update - 1件更新
        update_mapping(1, {'priority': 4})
        updated = get_mapping_by_id(1)
        assert updated['priority'] == 4

        # 4. Delete - 1件削除
        delete_mapping(2)
        mappings = get_all_mappings()
        assert len(mappings) == 2

        # 5. 最終確認
        remaining_ids = [m['id'] for m in mappings]
        assert 1 in remaining_ids
        assert 2 not in remaining_ids
        assert 3 in remaining_ids
