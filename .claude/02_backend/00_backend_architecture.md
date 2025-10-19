# バックエンドアーキテクチャ

## 技術スタック

**Webフレームワーク**
- Flask 3.1.2（軽量Webフレームワーク）
- Werkzeug 3.1以上（WSGIツールキット）
- Gunicorn 23.0以上（本番環境用WSGIサーバー）

**主要ライブラリ**
- pandas 2.x（CSV解析・データ処理）
- gspread 6.x（Google Sheets API簡易ラッパー）
- google-auth 2.x（Google OAuth認証）
- chardet 5.x（文字コード自動検出）
- python-dotenv 1.x（環境変数管理）

**Flaskエコシステム**
- Jinja2 3.x（テンプレートエンジン）
- ItsDangerous 2.2以上（セキュアなセッション管理）
- Click（コマンドラインインターフェース）
- Blinker 1.9以上（シグナルサポート）

## アプリケーション構成

```
project_root/
├── app.py                    # メインアプリケーション
├── config/
│   ├── mapping.json          # カテゴリマッピング
│   └── service_account.json  # Google認証情報
├── templates/                # Jinja2テンプレート
│   ├── index.html
│   ├── mapping.html
│   └── result.html
├── static/                   # 静的ファイル
│   ├── css/style.css
│   └── js/app.js
├── modules/                  # ビジネスロジック
│   ├── csv_parser.py        # CSV解析
│   ├── category_matcher.py  # カテゴリ判定
│   └── sheets_client.py     # Google Sheets連携
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 認証方式

**Googleサービスアカウント認証**
- サービスアカウント: `creditapi@creditapi-470614.iam.gserviceaccount.com`
- プロジェクトID: `creditapi-470614`
- 完全自動化、ブラウザ認証不要
- 認証情報ファイル（JSON）をDocker内に配置