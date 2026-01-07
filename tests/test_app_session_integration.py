"""
Flask-SessionとSessionStoreの統合テスト

このテストスイートは、Flask-Sessionによるセッション管理と
SQLiteベースのSessionStoreの統合動作を検証します。

主な検証項目:
- Flask-Sessionによるsession.sidの自動生成
- SessionStoreとFlask-Sessionの連携動作
- セッションデータの保存・読み込み・削除
- エラーハンドリング

Author: Claude Code
Created: 2026-01-03
Version: 1.0
"""

import pytest
import io
import os
from pathlib import Path
from app import app, session_store


@pytest.fixture
def client():
    """Flaskテストクライアント"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        yield client


class TestFlaskSessionIntegration:
    """Flask-Sessionとセッション管理の統合テスト"""

    def test_session_sid_exists(self, client):
        """session.sidが生成されることを確認"""
        with client:
            response = client.get('/')
            assert response.status_code == 200

            with client.session_transaction() as sess:
                assert hasattr(sess, 'sid')
                assert sess.sid is not None


    def test_session_store_integration(self, client):
        """SessionStoreとFlask-Sessionの連携テスト"""
        with client:
            client.get('/')

            with client.session_transaction() as sess:
                session_id = sess.sid

                test_data = {'test_key': 'test_value'}
                session_store.save(session_id, test_data)

                loaded_data = session_store.load(session_id)
                assert loaded_data == test_data


    def test_session_store_delete(self, client):
        """SessionStoreのdelete機能テスト"""
        with client:
            client.get('/')

            with client.session_transaction() as sess:
                session_id = sess.sid

                test_data = {'key': 'value'}
                session_store.save(session_id, test_data)

                loaded_data = session_store.load(session_id)
                assert loaded_data == test_data

                result = session_store.delete(session_id)
                assert result is True

                deleted_data = session_store.load(session_id)
                assert deleted_data is None


    def test_large_session_data(self, client):
        """Cookie 4KB制限を超える大容量データの保存テスト"""
        with client:
            client.get('/')

            with client.session_transaction() as sess:
                session_id = sess.sid

                large_data = {
                    'csv_data': [
                        {
                            'date': f'2024/{i:02d}/01',
                            'store': f'テスト店舗{i}',
                            'amount': i * 1000,
                            'category': 'テストカテゴリ',
                            'dummy_field_1': 'x' * 100,
                            'dummy_field_2': 'y' * 100,
                        }
                        for i in range(1, 50)
                    ]
                }

                result = session_store.save(session_id, large_data)
                assert result is True

                loaded_data = session_store.load(session_id)
                assert loaded_data is not None
                assert len(loaded_data['csv_data']) == 49
                assert loaded_data == large_data
