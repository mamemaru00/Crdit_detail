# システム構成図

## 全体構成

```
[ユーザーPC]
    ↓ (ブラウザアクセス http://localhost:5000)
[Dockerコンテナ群]
  ├ Nginxリバースプロキシ（ポート80→5000）
  │   ├ gzip圧縮（JSON/CSS/JS）
  │   ├ NaN→null変換フィルター（JSON応答）
  │   ├ セキュリティヘッダー（X-Content-Type-Options, X-Frame-Options, X-XSS-Protection）
  │   └ ファイルサイズ制限（10MB、DoS保護）
  │       ↓ (プロキシ http://web:5000)
  └ Webアプリケーション（Flask）
      ├ フロントエンド（Jinja2テンプレート + Bootstrap 5.3）
      └ バックエンド（Flaskルート）
          ├ CSV解析エンジン（pandas、chardet）
          ├ カテゴリ判定エンジン（パターンマッチング）
          ├ マッピング管理（JSON CRUD）
          ├ セッションストア（SQLite、WALモード）
          └ スプレッドシート連携（gspread）
              ↓ (サービスアカウント認証)
      [Google Sheets API]
          ↓
      [Googleスプレッドシート]
        ├ 2025年シート
        ├ 2024年シート
        └ ...

[設定ファイル/DB]
  - マッピングテーブル（data/mapping.json）
  - サービスアカウント認証情報（config/service_account.json）
  - セッションDB（data/sessions/sessions.db）
```

## システム構成の特徴

### ローカル環境
- Docker Desktop上で動作
- 外部公開なし（セキュア）
- ポート5000でローカルアクセス

### アプリケーション層
- **Nginx**: リバースプロキシ、gzip圧縮、NaN変換、セキュリティヘッダー
- **Flask 3.1.2**: Webフレームワーク
- **Jinja2**: テンプレートエンジン
- **Gunicorn**: 本番用WSGIサーバー

### データ層
- JSONファイル（マッピングテーブル）
- Google Sheets（家計簿データ）

### 外部連携
- Google Sheets API（サービスアカウント認証）
- インターネット接続必須

## 技術スタック

### コンテナ化
- Docker Desktop 4.44以上
- Docker Compose v2以上

### バックエンド
- Python 3.14.0
- Flask 3.1.2
- pandas 2.x（データ処理）
- gspread 6.x（Google Sheets連携）

### フロントエンド
- HTML5/CSS3/JavaScript
- Bootstrap 5.3
- Jinja2テンプレート

### 認証
- Googleサービスアカウント
- サービスアカウントメール: creditapi@creditapi-470614.iam.gserviceaccount.com
- プロジェクトID: creditapi-470614