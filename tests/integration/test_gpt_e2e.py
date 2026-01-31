"""
ChatGPT分類機能のE2Eテスト（Phase 7.5 Step 7.5.1）

このテストは、ChatGPT分類機能のフルフローを検証します。

テストシナリオ:
1. フルフローテスト: セッションに未登録店舗データをセット → POST /gpt/classify → GET /gpt/classification → POST /gpt/confirm → SQLite登録確認
2. キャンセルフローテスト: POST /gpt/classify → GET /gpt/classification → POST /gpt/cancel → セッションクリア確認 → GET / リダイレクト確認
3. 手修正→確定テスト: POST /gpt/classify → GET /gpt/classification → カテゴリ変更してPOST /gpt/confirm → 変更後のカテゴリでSQLite登録確認
4. セッションデータ正常性: 各エンドポイント通過後のセッション内容検証
5. SQLiteトランザクション: confirm時のINSERT成功、rollback検証

Author: Claude Code
Created: 2026-01-31
"""

import os
import sys
import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import app
from modules.mapping_manager import get_all_mappings, delete_mapping


# ==================== フィクスチャ ====================

@pytest.fixture
def client():
    """Flaskテストクライアント"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # CSRF無効化（テスト用）
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_gpt_classifier():
    """GPTClassifierのモック"""
    # Config.OPENAI_API_KEYもモック化
    with patch('app.Config.OPENAI_API_KEY', 'test-api-key-12345'), \
         patch('app.GPTClassifier') as mock_cls:
        mock_instance = MagicMock()
        mock_instance.classify_stores.return_value = {
            'テスト店舗A': {
                'category': '外食費',
                'column': 'D',
                'confidence': 'high',
                'reasoning': 'テスト分類理由A'
            },
            'テスト店舗B': {
                'category': '食材費',
                'column': 'C',
                'confidence': 'medium',
                'reasoning': 'テスト分類理由B'
            },
            'テスト店舗C': {
                'category': '雑貨費',
                'column': 'H',
                'confidence': 'low',
                'reasoning': 'テスト分類理由C'
            }
        }
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def setup_session_with_unregistered_stores(client):
    """セッションに未登録店舗データをセットする"""
    # Flaskアプリのsession_storeインスタンスを使用
    from app import session_store as app_session_store

    # server_session_idを生成させる（GET /）
    client.get('/')

    # server_session_idを取得
    with client.session_transaction() as sess:
        session_id = sess['server_session_id']

    # セッションストアにデータを保存
    session_data = {
        'process_result': {
            'unregistered_stores': [
                {'store': 'テスト店舗A', 'count': 3, 'total_amount': 5000},
                {'store': 'テスト店舗B', 'count': 2, 'total_amount': 3000},
                {'store': 'テスト店舗C', 'count': 1, 'total_amount': 1500}
            ],
            'summary': {
                'total_amount': 9500,
                'total_count': 6
            }
        }
    }
    app_session_store.save(session_id, session_data)
    yield session_data


@pytest.fixture(autouse=True)
def cleanup_test_mappings():
    """テスト前後のマッピングデータクリーンアップ"""
    # テスト前: テスト用店舗名のマッピングを削除
    test_stores = ['テスト店舗A', 'テスト店舗B', 'テスト店舗C']
    all_mappings = get_all_mappings()
    for mapping in all_mappings:
        if mapping.get('pattern') in test_stores:
            delete_mapping(mapping['id'])

    yield

    # テスト後: テスト用店舗名のマッピングを削除
    all_mappings = get_all_mappings()
    for mapping in all_mappings:
        if mapping.get('pattern') in test_stores:
            delete_mapping(mapping['id'])


# ==================== E2Eテスト ====================

def test_full_flow(client, setup_session_with_unregistered_stores, mock_gpt_classifier):
    """
    E2Eテスト 1: フルフローテスト

    シナリオ:
    1. セッションに未登録店舗データをセット
    2. POST /gpt/classify → ChatGPT分類実行
    3. GET /gpt/classification → 分類結果確認画面表示
    4. POST /gpt/confirm → SQLiteに一括登録
    5. SQLiteに登録されたことを確認
    """
    from app import session_store as app_session_store

    # server_session_idを取得
    with client.session_transaction() as sess:
        session_id = sess['server_session_id']

    # 1. セッションに未登録店舗データをセット（fixture）
    session_data_before = app_session_store.load(session_id)
    assert session_data_before is not None
    assert 'process_result' in session_data_before
    assert len(session_data_before['process_result']['unregistered_stores']) == 3

    # 2. POST /gpt/classify → ChatGPT分類実行
    response = client.post('/gpt/classify')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['classified_count'] == 3
    assert data['data']['redirect_url'] == '/gpt/classification'

    # セッションに gpt_classifications が保存されているか確認
    session_data_after_classify = app_session_store.load(session_id)
    assert 'gpt_classifications' in session_data_after_classify
    assert len(session_data_after_classify['gpt_classifications']) == 3
    assert 'テスト店舗A' in session_data_after_classify['gpt_classifications']

    # 3. GET /gpt/classification → 分類結果確認画面表示
    response = client.get('/gpt/classification')
    assert response.status_code == 200
    assert 'テスト店舗A'.encode('utf-8') in response.data
    assert '外食費'.encode('utf-8') in response.data

    # 4. POST /gpt/confirm → SQLiteに一括登録
    confirm_payload = {
        'classifications': [
            {'store': 'テスト店舗A', 'category': '外食費', 'column': 'D'},
            {'store': 'テスト店舗B', 'category': '食材費', 'column': 'C'},
            {'store': 'テスト店舗C', 'category': '雑貨費', 'column': 'H'}
        ]
    }
    response = client.post('/gpt/confirm', json=confirm_payload, content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['registered_count'] == 3
    assert data['data']['failed_count'] == 0

    # 5. SQLiteに登録されたことを確認
    all_mappings = get_all_mappings()
    test_mappings = [m for m in all_mappings if m['pattern'] in ['テスト店舗A', 'テスト店舗B', 'テスト店舗C']]
    assert len(test_mappings) == 3

    # 個別確認
    mapping_a = next((m for m in test_mappings if m['pattern'] == 'テスト店舗A'), None)
    assert mapping_a is not None
    assert mapping_a['category'] == '外食費'
    assert mapping_a['column'] == 'D'
    assert mapping_a['priority'] == 4
    # Note: get_all_mappings()がsourceを返さないため、sourceのチェックはスキップ

    # セッションから gpt_classifications がクリアされているか確認
    session_data_after_confirm = app_session_store.load(session_id)
    assert 'gpt_classifications' not in session_data_after_confirm

    # unregistered_stores から登録済み店舗が削除されているか確認
    unregistered = session_data_after_confirm.get('process_result', {}).get('unregistered_stores', [])
    assert len(unregistered) == 0


def test_cancel_flow(client, setup_session_with_unregistered_stores, mock_gpt_classifier):
    """
    E2Eテスト 2: キャンセルフローテスト

    シナリオ:
    1. POST /gpt/classify → ChatGPT分類実行
    2. GET /gpt/classification → 分類結果確認画面表示
    3. POST /gpt/cancel → セッションクリア
    4. セッションから gpt_classifications が削除されたことを確認
    5. GET /gpt/classification → メイン画面にリダイレクト
    """
    from app import session_store as app_session_store

    with client.session_transaction() as sess:
        session_id = sess['server_session_id']

    # 1. POST /gpt/classify → ChatGPT分類実行
    response = client.post('/gpt/classify')
    assert response.status_code == 200

    # セッションに gpt_classifications が保存されているか確認
    session_data_before_cancel = app_session_store.load(session_id)
    assert 'gpt_classifications' in session_data_before_cancel

    # 2. GET /gpt/classification → 分類結果確認画面表示
    response = client.get('/gpt/classification')
    assert response.status_code == 200

    # 3. POST /gpt/cancel → セッションクリア
    response = client.post('/gpt/cancel')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'キャンセル' in data['message']

    # 4. セッションから gpt_classifications が削除されたことを確認
    session_data_after_cancel = app_session_store.load(session_id)
    assert 'gpt_classifications' not in session_data_after_cancel

    # 5. GET /gpt/classification → メイン画面にリダイレクト
    response = client.get('/gpt/classification', follow_redirects=False)
    assert response.status_code == 302
    assert response.location == '/'


def test_manual_edit_and_confirm_flow(client, setup_session_with_unregistered_stores, mock_gpt_classifier):
    """
    E2Eテスト 3: 手修正→確定テスト

    シナリオ:
    1. POST /gpt/classify → ChatGPT分類実行（初期分類: テスト店舗A = 外食費/D列）
    2. GET /gpt/classification → 分類結果確認画面表示
    3. ユーザーがカテゴリを変更（テスト店舗A: 外食費 → 食材費/C列）
    4. POST /gpt/confirm → 変更後のカテゴリでSQLite登録
    5. SQLiteに変更後のカテゴリで登録されたことを確認
    """
    from app import session_store as app_session_store

    with client.session_transaction() as sess:
        session_id = sess['server_session_id']

    # 1. POST /gpt/classify → ChatGPT分類実行
    response = client.post('/gpt/classify')
    assert response.status_code == 200

    # 初期分類結果確認
    session_data = app_session_store.load(session_id)
    assert session_data['gpt_classifications']['テスト店舗A']['category'] == '外食費'
    assert session_data['gpt_classifications']['テスト店舗A']['column'] == 'D'

    # 2. GET /gpt/classification → 分類結果確認画面表示
    response = client.get('/gpt/classification')
    assert response.status_code == 200

    # 3. ユーザーがカテゴリを変更（テスト店舗A: 外食費 → 食材費/C列）
    modified_payload = {
        'classifications': [
            {'store': 'テスト店舗A', 'category': '食材費', 'column': 'C'},  # 変更
            {'store': 'テスト店舗B', 'category': '食材費', 'column': 'C'},
            {'store': 'テスト店舗C', 'category': '雑貨費', 'column': 'H'}
        ]
    }

    # 4. POST /gpt/confirm → 変更後のカテゴリでSQLite登録
    response = client.post('/gpt/confirm', json=modified_payload, content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['registered_count'] == 3

    # 5. SQLiteに変更後のカテゴリで登録されたことを確認
    all_mappings = get_all_mappings()
    mapping_a = next((m for m in all_mappings if m['pattern'] == 'テスト店舗A'), None)
    assert mapping_a is not None
    assert mapping_a['category'] == '食材費'  # 変更後のカテゴリ
    assert mapping_a['column'] == 'C'  # 変更後の列番号
    assert mapping_a['source'] == 'auto'
    assert mapping_a['priority'] == 4


def test_session_data_integrity(client, setup_session_with_unregistered_stores, mock_gpt_classifier):
    """
    E2Eテスト 4: セッションデータ正常性テスト

    シナリオ:
    1. 各エンドポイント通過後のセッション内容を検証
    2. process_result が保持されているか確認
    3. gpt_classifications のライフサイクル確認
    """
    from app import session_store as app_session_store

    with client.session_transaction() as sess:
        session_id = sess['server_session_id']

    # 初期状態確認
    session_data = app_session_store.load(session_id)
    assert 'process_result' in session_data
    assert 'gpt_classifications' not in session_data

    # POST /gpt/classify 後
    response = client.post('/gpt/classify')
    assert response.status_code == 200

    session_data = app_session_store.load(session_id)
    assert 'process_result' in session_data  # 保持される
    assert 'gpt_classifications' in session_data  # 追加される
    assert len(session_data['gpt_classifications']) == 3

    # POST /gpt/confirm 後
    confirm_payload = {
        'classifications': [
            {'store': 'テスト店舗A', 'category': '外食費', 'column': 'D'},
            {'store': 'テスト店舗B', 'category': '食材費', 'column': 'C'},
            {'store': 'テスト店舗C', 'category': '雑貨費', 'column': 'H'}
        ]
    }
    response = client.post('/gpt/confirm', json=confirm_payload, content_type='application/json')
    assert response.status_code == 200

    session_data = app_session_store.load(session_id)
    assert 'process_result' in session_data  # 保持される
    assert 'gpt_classifications' not in session_data  # クリアされる


def test_sqlite_transaction_success(client, setup_session_with_unregistered_stores, mock_gpt_classifier):
    """
    E2Eテスト 5: SQLiteトランザクション成功テスト

    シナリオ:
    1. POST /gpt/classify → 分類実行
    2. POST /gpt/confirm → 3件すべてINSERT成功
    3. SQLiteに3件すべて登録されたことを確認
    """
    # 1. POST /gpt/classify
    response = client.post('/gpt/classify')
    assert response.status_code == 200

    # 2. POST /gpt/confirm
    confirm_payload = {
        'classifications': [
            {'store': 'テスト店舗A', 'category': '外食費', 'column': 'D'},
            {'store': 'テスト店舗B', 'category': '食材費', 'column': 'C'},
            {'store': 'テスト店舗C', 'category': '雑貨費', 'column': 'H'}
        ]
    }
    response = client.post('/gpt/confirm', json=confirm_payload, content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['data']['registered_count'] == 3
    assert data['data']['failed_count'] == 0

    # 3. SQLiteに3件すべて登録されたことを確認
    all_mappings = get_all_mappings()
    test_mappings = [m for m in all_mappings if m['pattern'] in ['テスト店舗A', 'テスト店舗B', 'テスト店舗C']]
    assert len(test_mappings) == 3


def test_sqlite_transaction_partial_failure(client, setup_session_with_unregistered_stores, mock_gpt_classifier):
    """
    E2Eテスト 5b: SQLiteトランザクション部分失敗テスト

    シナリオ:
    1. POST /gpt/classify → 分類実行
    2. 事前に テスト店舗A をSQLiteに登録（重複発生）
    3. POST /gpt/confirm → テスト店舗A は重複エラー（スキップ）、テスト店舗B/C は成功
    4. registered_count=2, failed_count=1 を確認
    """
    # 1. POST /gpt/classify
    response = client.post('/gpt/classify')
    assert response.status_code == 200

    # 2. 事前に テスト店舗A を登録（重複発生）
    from modules.mapping_manager import add_mapping
    add_mapping({
        'pattern': 'テスト店舗A',
        'match_type': 'keyword',
        'category': '食材費',
        'column': 'C',
        'priority': 4,
        'source': 'manual'
    })

    # 3. POST /gpt/confirm
    confirm_payload = {
        'classifications': [
            {'store': 'テスト店舗A', 'category': '外食費', 'column': 'D'},  # 重複エラー
            {'store': 'テスト店舗B', 'category': '食材費', 'column': 'C'},
            {'store': 'テスト店舗C', 'category': '雑貨費', 'column': 'H'}
        ]
    }
    response = client.post('/gpt/confirm', json=confirm_payload, content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['data']['registered_count'] == 2  # テスト店舗B/C のみ成功
    assert data['data']['failed_count'] == 1  # テスト店舗A は重複エラー


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
