# システム構成図

## 全体構成

```
[ユーザーPC]
    ↓ (ブラウザアクセス http://localhost:5000)
[Dockerコンテナ]
  - Webアプリケーション（Flask）
    ├ フロントエンド（Jinja2テンプレート）
    └ バックエンド（Flaskルート）
        ├ CSV解析エンジン
        ├ カテゴリ判定エンジン
        ├ マッピング管理
        └ スプレッドシート連携
            ↓ (サービスアカウント認証)
    [Google Sheets API]
        ↓
    [Googleスプレッドシート]
      ├ 2025年シート
      ├ 2024年シート
      └ ...
    
[設定ファイル/DB]
  - マッピングテーブル（JSON）
  - サービスアカウント認証情報（JSON）
```

## システム構成の特徴

### ローカル環境
- Docker Desktop上で動作
- 外部公開なし（セキュア）
- ポート5000でローカルアクセス

### アプリケーション層
- Flask 3.1.2（Webフレームワーク）
- Jinja2（テンプレートエンジン）
- Gunicorn（本番用WSGIサーバー）

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