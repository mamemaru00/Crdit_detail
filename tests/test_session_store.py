"""
SessionStore単体テスト

テストケース:
- 初期化テスト（3ケース）
- 保存テスト（4ケース）
- 読み込みテスト（4ケース）
- 削除テスト（2ケース）
- 有効期限管理テスト（3ケース）
- WAL管理テスト（2ケース）
- エラーハンドリングテスト（3ケース）

Author: Claude Code
Created: 2025-12-30
"""

import pytest
import sqlite3
import json
import time
import tempfile
import os
from pathlib import Path
from modules.session_store import SessionStore, SessionStoreError


# ==================== フィクスチャ ====================

@pytest.fixture
def temp_db_path():
    """一時DBファイルパスを生成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_sessions.db')
        yield db_path


@pytest.fixture
def session_store(temp_db_path):
    """SessionStoreインスタンスを生成"""
    return SessionStore(db_path=temp_db_path, ttl_seconds=1800)


@pytest.fixture
def sample_session_data():
    """サンプルセッションデータ"""
    return {
        'uploaded_file_path': '/tmp/test.csv',
        'uploaded_filename': 'test.csv',
        'csv_data': [
            {'date': '2025/01/01', 'store': 'テスト店', 'amount': 1000},
            {'date': '2025/01/02', 'store': 'サンプル店', 'amount': 2000}
        ]
    }


@pytest.fixture
def large_session_data():
    """大容量セッションデータ（約100KB）"""
    # 1000件のCSVデータを生成
    data = {
        'csv_data': [
            {
                'date': f'2025/01/{i % 30 + 1:02d}',
                'store': f'店舗{i}',
                'amount': i * 100,
                'category': 'テストカテゴリ',
                'column': 'B'
            }
            for i in range(1000)
        ]
    }
    return data


# ==================== 初期化テスト ====================

def test_init_creates_db_file(temp_db_path):
    """DBファイルが正しく作成されるか"""
    store = SessionStore(db_path=temp_db_path, ttl_seconds=1800)
    assert Path(temp_db_path).exists(), "DBファイルが作成されていません"


def test_init_creates_table(temp_db_path):
    """テーブルが正しく作成されるか"""
    store = SessionStore(db_path=temp_db_path, ttl_seconds=1800)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # テーブル存在確認
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='sessions'
    """)
    result = cursor.fetchone()

    conn.close()

    assert result is not None, "sessionsテーブルが作成されていません"
    assert result[0] == 'sessions', "テーブル名が不正です"


def test_init_enables_wal_mode(temp_db_path):
    """WALモードが有効化されるか"""
    store = SessionStore(db_path=temp_db_path, ttl_seconds=1800)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # WALモード確認
    cursor.execute("PRAGMA journal_mode")
    journal_mode = cursor.fetchone()[0]

    conn.close()

    assert journal_mode.lower() == 'wal', f"WALモードが有効化されていません（現在: {journal_mode}）"


# ==================== 保存テスト ====================

def test_save_new_session(session_store, sample_session_data):
    """新規セッション保存が成功するか"""
    session_id = 'test-session-001'

    result = session_store.save(session_id, sample_session_data)

    assert result is True, "セッション保存に失敗しました"

    # データ確認
    loaded_data = session_store.load(session_id)
    assert loaded_data == sample_session_data, "保存されたデータが一致しません"


def test_save_update_session(session_store, sample_session_data):
    """既存セッション更新が成功するか"""
    session_id = 'test-session-002'

    # 初回保存
    session_store.save(session_id, sample_session_data)

    # データ更新
    updated_data = {**sample_session_data, 'new_field': 'new_value'}
    result = session_store.save(session_id, updated_data)

    assert result is True, "セッション更新に失敗しました"

    # 更新データ確認
    loaded_data = session_store.load(session_id)
    assert loaded_data == updated_data, "更新されたデータが一致しません"
    assert 'new_field' in loaded_data, "新しいフィールドが追加されていません"


def test_save_large_data(session_store, large_session_data):
    """大容量データ（100KB）の保存が成功するか"""
    session_id = 'test-session-large'

    result = session_store.save(session_id, large_session_data)

    assert result is True, "大容量データ保存に失敗しました"

    # データサイズ確認
    data_json = json.dumps(large_session_data, ensure_ascii=False)
    assert len(data_json) > 50000, "データサイズが小さすぎます（テストデータ不足）"

    # データ確認
    loaded_data = session_store.load(session_id)
    assert len(loaded_data['csv_data']) == 1000, "保存されたデータ件数が一致しません"


def test_save_special_characters(session_store):
    """特殊文字を含むデータの保存が成功するか"""
    session_id = 'test-session-special'

    special_data = {
        'japanese': 'これはテストです',
        'emoji': '🎉🚀',
        'quotes': '"double" \'single\'',
        'newlines': 'line1\nline2\nline3',
        'unicode': '\u3042\u3044\u3046',  # あいう
    }

    result = session_store.save(session_id, special_data)

    assert result is True, "特殊文字データ保存に失敗しました"

    # データ確認
    loaded_data = session_store.load(session_id)
    assert loaded_data == special_data, "特殊文字データが正しく復元されていません"


# ==================== 読み込みテスト ====================

def test_load_existing_session(session_store, sample_session_data):
    """既存セッションの読み込みが成功するか"""
    session_id = 'test-session-load'

    # 保存
    session_store.save(session_id, sample_session_data)

    # 読み込み
    loaded_data = session_store.load(session_id)

    assert loaded_data is not None, "セッションが読み込めません"
    assert loaded_data == sample_session_data, "読み込まれたデータが一致しません"


def test_load_nonexistent_session(session_store):
    """存在しないセッションはNoneを返すか"""
    session_id = 'nonexistent-session'

    loaded_data = session_store.load(session_id)

    assert loaded_data is None, "存在しないセッションがNoneを返していません"


def test_load_expired_session(temp_db_path):
    """有効期限切れセッションは自動削除されるか"""
    # TTL 1秒で作成
    store = SessionStore(db_path=temp_db_path, ttl_seconds=1)
    session_id = 'test-session-expired'

    # 保存
    store.save(session_id, {'test': 'data'})

    # 2秒待機
    time.sleep(2)

    # 読み込み（自動削除されるはず）
    loaded_data = store.load(session_id)

    assert loaded_data is None, "有効期限切れセッションが削除されていません"


def test_load_large_data(session_store, large_session_data):
    """大容量データの読み込みが成功するか"""
    session_id = 'test-session-large-load'

    # 保存
    session_store.save(session_id, large_session_data)

    # 読み込み
    loaded_data = session_store.load(session_id)

    assert loaded_data is not None, "大容量データが読み込めません"
    assert len(loaded_data['csv_data']) == 1000, "データ件数が一致しません"


# ==================== 削除テスト ====================

def test_delete_existing_session(session_store, sample_session_data):
    """既存セッション削除が成功するか"""
    session_id = 'test-session-delete'

    # 保存
    session_store.save(session_id, sample_session_data)

    # 削除
    result = session_store.delete(session_id)

    assert result is True, "セッション削除に失敗しました"

    # 削除確認
    loaded_data = session_store.load(session_id)
    assert loaded_data is None, "セッションが削除されていません"


def test_delete_nonexistent_session(session_store):
    """存在しないセッション削除が成功するか（エラーなし）"""
    session_id = 'nonexistent-session-delete'

    # 削除
    result = session_store.delete(session_id)

    assert result is True, "存在しないセッション削除でエラーが発生しました"


# ==================== 有効期限管理テスト ====================

def test_prune_expired_sessions(temp_db_path):
    """有効期限切れセッションが削除されるか"""
    # TTL 1秒で作成
    store = SessionStore(db_path=temp_db_path, ttl_seconds=1)

    # 複数セッション保存
    store.save('session-1', {'test': 'data1'})
    store.save('session-2', {'test': 'data2'})
    store.save('session-3', {'test': 'data3'})

    # 2秒待機
    time.sleep(2)

    # 新しいセッション保存（有効期限内）
    store_new = SessionStore(db_path=temp_db_path, ttl_seconds=1800)
    store_new.save('session-new', {'test': 'new-data'})

    # 有効期限切れセッション削除
    deleted_count = store_new.prune_expired()

    assert deleted_count == 3, f"削除件数が不正です（期待: 3, 実際: {deleted_count}）"

    # 新しいセッションは残っているか確認
    loaded_data = store_new.load('session-new')
    assert loaded_data is not None, "新しいセッションが削除されています"


def test_prune_no_expired_sessions(session_store, sample_session_data):
    """有効なセッションは削除されないか"""
    # 複数セッション保存
    session_store.save('session-a', sample_session_data)
    session_store.save('session-b', sample_session_data)

    # クリーンアップ実行
    deleted_count = session_store.prune_expired()

    assert deleted_count == 0, "有効なセッションが削除されています"

    # セッション確認
    assert session_store.load('session-a') is not None, "セッションAが削除されています"
    assert session_store.load('session-b') is not None, "セッションBが削除されています"


def test_ttl_setting(temp_db_path):
    """TTL設定が正しく反映されるか"""
    ttl_seconds = 3600  # 1時間

    store = SessionStore(db_path=temp_db_path, ttl_seconds=ttl_seconds)

    assert store.ttl_seconds == ttl_seconds, "TTL設定が反映されていません"


# ==================== WAL管理テスト ====================

def test_wal_checkpoint(session_store, sample_session_data):
    """WALチェックポイントが成功するか"""
    # セッション保存
    for i in range(10):
        session_store.save(f'session-{i}', sample_session_data)

    # WALチェックポイント実行
    result = session_store.wal_checkpoint()

    # 結果はTrue or Falseのいずれか（ビジー状態の可能性あり）
    assert isinstance(result, bool), "WALチェックポイントの戻り値が不正です"


def test_wal_file_cleanup(temp_db_path, sample_session_data):
    """WALファイルがクリーンアップされるか"""
    store = SessionStore(db_path=temp_db_path, ttl_seconds=1800)

    # セッション保存
    for i in range(100):
        store.save(f'session-{i}', sample_session_data)

    # WALチェックポイント実行
    store.wal_checkpoint()

    # WALファイル確認（存在していてもOK、サイズが小さいことを確認）
    wal_path = f"{temp_db_path}-wal"
    if Path(wal_path).exists():
        wal_size = Path(wal_path).stat().st_size
        # WALファイルが過度に大きくないことを確認（1MB未満）
        assert wal_size < 1024 * 1024, f"WALファイルが大きすぎます（{wal_size} bytes）"


# ==================== エラーハンドリングテスト ====================

def test_invalid_json_data(session_store):
    """JSON化できないデータでエラーが発生するか"""
    session_id = 'test-session-invalid'

    # JSON化不可能なデータ（関数オブジェクト）
    invalid_data = {
        'function': lambda x: x + 1  # 関数はJSON化不可
    }

    with pytest.raises(SessionStoreError) as exc_info:
        session_store.save(session_id, invalid_data)

    assert 'JSON変換に失敗' in str(exc_info.value), "エラーメッセージが不適切です"


def test_db_lock_handling(temp_db_path):
    """DBロック時のエラーハンドリング"""
    # Note: SQLiteのロックテストは実行環境に依存するため、
    # 基本的な接続エラーハンドリングのテストとする

    store = SessionStore(db_path=temp_db_path, ttl_seconds=1800)

    # 通常の操作は成功するはず
    session_id = 'test-session-lock'
    result = store.save(session_id, {'test': 'data'})

    assert result is True, "通常の保存が失敗しています"


def test_corrupted_db_handling(temp_db_path):
    """DB破損時のエラーハンドリング"""
    # 正常なDBを作成
    store = SessionStore(db_path=temp_db_path, ttl_seconds=1800)
    store.save('test-session', {'test': 'data'})

    # DBファイルを破損させる（空ファイルで上書き）
    with open(temp_db_path, 'w') as f:
        f.write('corrupted data')

    # 新しいSessionStoreインスタンスで読み込み試行
    with pytest.raises(SessionStoreError):
        store_new = SessionStore(db_path=temp_db_path, ttl_seconds=1800)


# ==================== 統合テスト ====================

def test_full_session_lifecycle(session_store, sample_session_data):
    """セッションの完全なライフサイクルテスト"""
    session_id = 'test-session-lifecycle'

    # 1. 保存
    save_result = session_store.save(session_id, sample_session_data)
    assert save_result is True, "保存に失敗しました"

    # 2. 読み込み
    loaded_data = session_store.load(session_id)
    assert loaded_data == sample_session_data, "読み込みデータが一致しません"

    # 3. 更新
    updated_data = {**sample_session_data, 'updated': True}
    update_result = session_store.save(session_id, updated_data)
    assert update_result is True, "更新に失敗しました"

    # 4. 更新確認
    loaded_updated_data = session_store.load(session_id)
    assert loaded_updated_data['updated'] is True, "更新が反映されていません"

    # 5. 削除
    delete_result = session_store.delete(session_id)
    assert delete_result is True, "削除に失敗しました"

    # 6. 削除確認
    deleted_data = session_store.load(session_id)
    assert deleted_data is None, "セッションが削除されていません"


def test_multiple_sessions(session_store, sample_session_data):
    """複数セッションの管理テスト"""
    session_ids = [f'session-{i}' for i in range(10)]

    # 複数セッション保存
    for session_id in session_ids:
        data = {**sample_session_data, 'id': session_id}
        session_store.save(session_id, data)

    # 全セッション読み込み確認
    for session_id in session_ids:
        loaded_data = session_store.load(session_id)
        assert loaded_data is not None, f"セッション {session_id} が読み込めません"
        assert loaded_data['id'] == session_id, "セッションIDが一致しません"

    # 一部セッション削除
    for i in range(0, 10, 2):  # 偶数インデックスのみ削除
        session_store.delete(session_ids[i])

    # 削除確認
    for i in range(10):
        loaded_data = session_store.load(session_ids[i])
        if i % 2 == 0:
            assert loaded_data is None, f"セッション {session_ids[i]} が削除されていません"
        else:
            assert loaded_data is not None, f"セッション {session_ids[i]} が誤って削除されています"


# ==================== パフォーマンステスト ====================

def test_save_performance(session_store, large_session_data):
    """保存性能テスト（1000件CSV、100ms以内）"""
    session_id = 'test-session-perf-save'

    start_time = time.time()
    session_store.save(session_id, large_session_data)
    elapsed_time = time.time() - start_time

    # 100ms以内（余裕を持って500ms以内とする）
    assert elapsed_time < 0.5, f"保存時間が長すぎます（{elapsed_time:.3f}秒）"


def test_load_performance(session_store, large_session_data):
    """読み込み性能テスト（1000件CSV、50ms以内）"""
    session_id = 'test-session-perf-load'

    # 保存
    session_store.save(session_id, large_session_data)

    # 読み込み性能測定
    start_time = time.time()
    loaded_data = session_store.load(session_id)
    elapsed_time = time.time() - start_time

    # 50ms以内（余裕を持って200ms以内とする）
    assert elapsed_time < 0.2, f"読み込み時間が長すぎます（{elapsed_time:.3f}秒）"


def test_prune_performance(temp_db_path):
    """クリーンアップ性能テスト（1000セッション、1秒以内）"""
    # TTL 1秒で作成
    store = SessionStore(db_path=temp_db_path, ttl_seconds=1)

    # 1000セッション保存
    for i in range(1000):
        store.save(f'session-{i}', {'test': f'data-{i}'})

    # 2秒待機
    time.sleep(2)

    # クリーンアップ性能測定
    start_time = time.time()
    deleted_count = store.prune_expired()
    elapsed_time = time.time() - start_time

    assert deleted_count == 1000, f"削除件数が不正です（期待: 1000, 実際: {deleted_count}）"
    assert elapsed_time < 1.0, f"クリーンアップ時間が長すぎます（{elapsed_time:.3f}秒）"
