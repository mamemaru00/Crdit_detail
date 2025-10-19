# 認証フロー

## 6.3 Google Sheets API認証フロー

### 6.3.1 サービスアカウント認証方式

本アプリケーションはGoogleサービスアカウント認証を使用します。

#### 認証設定手順

1. **Google Cloud Consoleでの設定**
   - プロジェクト作成（creditapi-470614）
   - Google Sheets APIの有効化
   - サービスアカウント作成（creditapi@creditapi-470614.iam.gserviceaccount.com）
   - JSONキーファイルのダウンロード（credentials.json）

2. **スプレッドシートへのアクセス権限付与**
   - 対象スプレッドシートを開く
   - 共有設定でサービスアカウントのメールアドレスを追加
   - 編集者権限を付与

3. **アプリケーション側の実装**
   ```python
   from google.oauth2 import service_account
   from googleapiclient.discovery import build
   
   SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
   credentials = service_account.Credentials.from_service_account_file(
       'credentials.json', scopes=SCOPES)
   service = build('sheets', 'v4', credentials=credentials)
   ```

### 6.3.2 認証エラー処理

- **認証ファイル未設置**: エラーメッセージ表示、設定手順案内
- **権限不足**: スプレッドシート共有設定の確認を促す
- **API制限超過**: リトライ処理実装、エラーログ記録

### 6.3.3 セキュリティ考慮事項

- credentials.jsonは.gitignoreに追加
- 環境変数での認証情報管理も対応可能
- スプレッドシートIDは設定ファイルまたはUI入力で管理
- サービスアカウントには最小権限の原則を適用