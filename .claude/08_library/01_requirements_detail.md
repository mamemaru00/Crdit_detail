# requirements.txt 詳細説明

## ライブラリの役割と用途

### Flask関連（Webアプリケーション基盤）
```txt
Flask==3.1.2
```
- 軽量Webフレームワーク
- ルーティング、テンプレートレンダリング
- `/upload`, `/mapping`等のエンドポイント提供

```txt
Werkzeug>=3.1
```
- WSGIツールキット（Flaskの基盤）
- HTTPリクエスト/レスポンス処理

```txt
Jinja2>=3.1
```
- テンプレートエンジン
- `index.html`, `mapping.html`等のレンダリング

```txt
ItsDangerous>=2.2
```
- セキュアなセッション管理
- Cookie署名、トークン生成

```txt
Click>=8.1
Blinker>=1.9
```
- CLIサポート、シグナル機能

### WSGIサーバー
```txt
gunicorn>=23.0
```
- 本番環境用WSGIサーバー
- 開発環境ではFlask開発サーバーを使用

### データ処理
```txt
pandas>=2.0,<3.0
```
- **CSV解析のコア機能**
- YYMMDD→YYYY/MM/DD変換
- 月別・カテゴリ別集計
- データフレーム操作

### Google Sheets連携
```txt
gspread>=6.0,<7.0
```
- Google Sheets API簡易ラッパー
- スプレッドシート読み書き
- セル更新、範囲取得

```txt
google-auth>=2.0,<3.0
```
- サービスアカウント認証
- `service_account.json`の読み込み

```txt
google-auth-oauthlib>=1.0,<2.0
google-auth-httplib2>=0.2
```
- OAuth認証サポート
- HTTP通信処理

### ユーティリティ
```txt
chardet>=5.0,<6.0
```
- **文字コード自動検出**
- Shift_JIS→UTF-8変換
- イオンカードCSV対応に必須

```txt
python-dotenv>=1.0,<2.0
```
- `.env`ファイルから環境変数読み込み
- スプレッドシートID等の管理

## バージョン指定の理由
- `==`: 完全固定（Flask等、互換性重視）
- `>=X.0,<Y.0`: メジャーバージョン固定（破壊的変更回避）
- `>=X.Y`: マイナーバージョン以上（セキュリティ更新適用）