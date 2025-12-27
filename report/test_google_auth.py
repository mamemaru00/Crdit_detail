#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets API認証テストスクリプト
Step 1.4の検証用
"""

import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

def test_authentication():
    """サービスアカウント認証のテスト"""
    try:
        # 認証情報の読み込み
        SERVICE_ACCOUNT_FILE = 'config/service_account.json'
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        print("✓ サービスアカウント認証情報の読み込み成功")
        print(f"  Service Account Email: {credentials.service_account_email}")
        print(f"  Project ID: {credentials.project_id}")

        # Google Sheets APIクライアントの構築
        service = build('sheets', 'v4', credentials=credentials)
        print("✓ Google Sheets APIクライアントの構築成功")

        print("\n認証テスト完了: すべて正常です")
        return True

    except FileNotFoundError:
        print("✗ エラー: config/service_account.json が見つかりません")
        print("  ファイルが正しく配置されているか確認してください")
        return False

    except Exception as e:
        print(f"✗ エラー: {type(e).__name__}")
        print(f"  詳細: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_authentication()
    sys.exit(0 if success else 1)
