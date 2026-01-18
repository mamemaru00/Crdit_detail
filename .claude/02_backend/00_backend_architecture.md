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
├── app.py                       # メインアプリケーション
├── config/
│   ├── mapping.json             # カテゴリマッピング（廃止予定、SQLite移行中）
│   └── service_account.json     # Google認証情報
├── data/
│   ├── mappings.db              # SQLiteマッピングDB（NEW）
│   ├── backups/                 # バックアップ
│   └── sessions/                # セッションストア
│       └── sessions.db          # SQLiteセッションDB
├── templates/                   # Jinja2テンプレート
│   ├── index.html
│   ├── mapping.html
│   ├── result.html
│   └── gpt_classification.html  # ChatGPT分類確認画面（NEW）
├── static/                      # 静的ファイル
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── main.js
│       ├── mapping.js
│       └── gpt_classification.js  # ChatGPT分類確認用JS（NEW）
├── modules/                     # ビジネスロジック
│   ├── csv_processor.py         # CSV解析
│   ├── category_logic.py        # カテゴリ判定
│   ├── sheets_api.py            # Google Sheets連携
│   ├── mapping_manager.py       # マッピング管理
│   ├── session_store.py         # セッションストア
│   └── gpt_classifier.py        # ChatGPT分類モジュール（NEW）
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

**ChatGPT API認証**（NEW）
- OpenAI API Key: 環境変数`OPENAI_API_KEY`で管理
- モデル: GPT-5
- 用途: 未登録店舗の自動カテゴリ分類

---

## ChatGPT分類フロー（NEW）

### 概要
未登録店舗をChatGPT APIで自動分類し、ユーザー確認後にSQLiteのstore_mappingsテーブルに登録する機能。

### フロー図
```
1. CSVアップロード
   ↓
2. CSV解析（csv_processor.py）
   ↓
3. 未登録店舗抽出（category_logic.py）
   ├─ 登録済み店舗 → 既存フロー
   └─ 未登録店舗 → ChatGPT分類フローへ
   ↓
4. ChatGPT API 呼び出し（gpt_classifier.py）
   ├─ 未登録店舗リスト送信
   ├─ カテゴリマスタ送信
   └─ 分類ルール送信
   ↓
5. ChatGPT 分類結果取得
   ↓
6. ユーザー確認画面表示（gpt_classification.html）
   ├─ 分類結果一覧表示
   ├─ 手修正可能
   └─ 確定ボタン
   ↓
7. 確定後、SQLite登録（mapping_manager.py）
   ├─ source='auto'
   ├─ priority=4
   └─ store_mappingsテーブルに一括INSERT
   ↓
8. 既存フローに合流
   ↓
9. カテゴリ判定（category_logic.py）
   ↓
10. Google Sheets 更新（sheets_api.py）
   ↓
11. 処理結果表示
```

### エラーハンドリング方針
- **GPT API失敗時**: デフォルトカテゴリ（H列: 雑貨費）で処理続行
- **SQLite書き込み失敗時**: 分類結果を破棄し、処理続行。最後に失敗内容を報告
- **ユーザーキャンセル時**: 未登録のまま処理続行、次回CSVアップロード時に再分類

### セキュリティ要件
- OpenAI API Key は環境変数で管理（`.env`ファイル、`.gitignore`対象）
- API呼び出し回数制限（レート制限対応）
- ユーザー確認を必須とし、自動登録は行わない

### パフォーマンス目標
- 未登録店舗50件を一括分類: 10秒以内
- ユーザー確認画面のレスポンス: 2秒以内