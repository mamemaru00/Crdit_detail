"""
server_session_idとSessionStoreの統合テスト

このテストスイートは、独自のserver_session_id機能と
SQLiteベースのSessionStoreの統合動作を検証します。

主な検証項目:
- server_session_idの自動生成
- SessionStoreとserver_session_idの連携動作
- セッションデータの保存・読み込み・削除
- セッション永続性
- Cookie 4KB制限対策

Author: Claude Code
Created: 2026-01-03
Updated: 2026-01-11
Version: 2.0
"""

import pytest
import io
import os
from pathlib import Path
from flask import session
from app import app, session_store


@pytest.fixture
def client():
    """Flaskテストクライアント"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        yield client


class TestServerSessionIdIntegration:
    """server_session_idとセッション管理の統合テスト"""

    def test_server_session_id_generated(self, client):
        """server_session_idが自動生成されることを確認"""
        response = client.get('/')
        assert response.status_code == 200

        with client.session_transaction() as sess:
            assert 'server_session_id' in sess
            assert len(sess['server_session_id']) == 32  # UUID4のhex形式


    def test_server_session_id_persistence(self, client):
        """server_session_idがリクエスト間で永続化されることを確認"""
        # 最初のリクエスト
        client.get('/')
        with client.session_transaction() as sess:
            session_id_1 = sess['server_session_id']

        # 2回目のリクエスト
        client.get('/')
        with client.session_transaction() as sess:
            session_id_2 = sess['server_session_id']

        assert session_id_1 == session_id_2  # 同じIDが保持される


    def test_session_store_integration(self, client):
        """SessionStoreとserver_session_idの連携テスト"""
        client.get('/')

        with client.session_transaction() as sess:
            session_id = sess['server_session_id']

        test_data = {'test_key': 'test_value'}
        session_store.save(session_id, test_data)

        loaded_data = session_store.load(session_id)
        assert loaded_data == test_data


    def test_session_store_delete(self, client):
        """SessionStoreのdelete機能テスト"""
        client.get('/')

        with client.session_transaction() as sess:
            session_id = sess['server_session_id']

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
        client.get('/')

        with client.session_transaction() as sess:
            session_id = sess['server_session_id']

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
