# ライブラリ構成概要

## コア技術スタック（2025年10月最新版）

### バックエンドフレームワーク
- **Python**: 3.14.0（2025年10月最新安定版）
- **Flask**: 3.1.2（軽量Webフレームワーク、2025年8月最新版）
- **Werkzeug**: 3.1以上（WSGIツールキット、Flaskの基盤）
- **Gunicorn**: 23.0以上（本番環境用WSGIサーバー）

### Flaskエコシステム
- **Jinja2**: 3.x（テンプレートエンジン、自動インストール）
- **ItsDangerous**: 2.2以上（セキュアなセッション管理）
- **Click**: コマンドラインインターフェース
- **Blinker**: 1.9以上（シグナルサポート）
- **Flask-CORS**: 6.0以上（CORS対応、必要に応じて）

### データ処理ライブラリ
- **pandas**: 2.x（CSV解析・データ処理の中核）
  - CSV読み込み・変換
  - データフレーム操作
  - 月別・カテゴリ別集計

### Google連携ライブラリ
- **gspread**: 6.x（Google Sheets API簡易ラッパー）
- **google-auth**: 2.x（Google OAuth認証）
- **google-auth-oauthlib**: 1.x（OAuth認証サポート）
- **google-auth-httplib2**: 0.2.x（HTTP通信）

### ユーティリティライブラリ
- **chardet**: 5.x（文字コード自動検出、Shift_JIS対応）
- **python-dotenv**: 1.x（環境変数管理）

### フロントエンド
- **HTML5/CSS3/JavaScript**
- **Bootstrap**: 5.3（UIフレームワーク）

### 開発・テストツール
- **pytest**（単体テスト）
- **black**（コードフォーマッター）
- **flake8**（リンター）

## インストール方法

```bash
pip install -r requirements.txt
```

詳細は`requirements_detail.md`を参照してください。