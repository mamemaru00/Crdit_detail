# バックエンドAPIルート設計

## エンドポイント一覧

### メイン画面
```
GET  /              # index.htmlを表示
```

### CSVアップロード・処理
```
POST /upload        # CSVファイルをアップロード
POST /preview       # CSVプレビューを取得
POST /process       # CSV処理を実行してスプレッドシート更新
```

### マッピング管理
```
GET  /mapping                 # マッピング管理画面を表示
GET  /mapping/list            # マッピング一覧をJSON取得（SQLite: store_mappings）
POST /mapping/add             # 新規マッピング追加（SQLite INSERT）
PUT  /mapping/edit/<id>       # マッピング編集（SQLite UPDATE）
DELETE /mapping/delete/<id>   # マッピング削除（SQLite DELETE）
```

### ChatGPT分類機能（NEW）
```
POST /gpt/classify            # 未登録店舗をChatGPTで自動分類
GET  /gpt/classification      # ChatGPT分類結果確認画面を表示
POST /gpt/confirm             # ユーザー確認後、SQLiteに一括登録
POST /gpt/cancel              # ChatGPT分類をキャンセル
```

### データ取得
```
GET  /result        # 処理結果を表示
GET  /download/log  # 処理ログをダウンロード
```

### 静的ファイル
```
GET  /static/<path> # CSS/JSファイル
```

---

## データフロー

### 従来フロー（～v1.0）
1. **CSVアップロード** (`POST /upload`)
   - Shift_JIS → UTF-8 変換
   - ファイル保存

2. **CSV解析** (`POST /preview`)
   - 明細データ抽出（6桁日付の行）
   - YYMMDD → YYYY/MM/DD 変換
   - プレビュー5件返却

3. **カテゴリ判定** (`POST /process`)
   - 各店舗名をマッピングテーブル（JSON）で照合
   - カテゴリと列番号を決定
   - 未登録店舗をリスト化

4. **Google Sheets連携**
   - サービスアカウント認証
   - 年シート・月行・カテゴリ列を特定
   - 既存値に新規金額を加算

5. **結果表示** (`GET /result`)
   - 月別・カテゴリ別サマリー
   - 未登録店舗リスト
   - 処理詳細ログ

---

### ChatGPT分類フロー（v2.0～）

1. **CSVアップロード** (`POST /upload`)
   - Shift_JIS → UTF-8 変換
   - ファイル保存

2. **CSV解析** (`POST /preview`)
   - 明細データ抽出（6桁日付の行）
   - YYMMDD → YYYY/MM/DD 変換
   - プレビュー5件返却

3. **カテゴリ判定** (`POST /process`)
   - 各店舗名をマッピングテーブル（SQLite: store_mappings）で照合
   - 登録済み店舗 → カテゴリと列番号を決定 → Step 6へ
   - 未登録店舗 → ChatGPT分類フローへ

4. **ChatGPT自動分類** (`POST /gpt/classify`)
   - 未登録店舗リスト抽出（ユニーク化）
   - カテゴリマスタ送信（C～V列定義）
   - ChatGPT API 呼び出し（gpt_classifier.py）
   - JSON形式で分類結果を受信
   - エラー時: デフォルトカテゴリ（H列: 雑貨費）で続行

5. **ユーザー確認** (`GET /gpt/classification`)
   - ChatGPT分類結果を一覧表示（gpt_classification.html）
   - 店舗名、分類結果（カテゴリ、列）、金額、出現回数を表示
   - ドロップダウンで手修正可能
   - 確定ボタン → `POST /gpt/confirm` へ
   - キャンセルボタン → `POST /gpt/cancel` へ

6. **分類結果登録** (`POST /gpt/confirm`)
   - ユーザー確認済み分類結果をSQLiteに一括INSERT
   - store_mappingsテーブルに登録
     - source='auto'
     - priority=4
   - トランザクション処理（全件成功 or 全件ロールバック）
   - 失敗時: エラーログ記録、ユーザーに通知

7. **Google Sheets連携**
   - サービスアカウント認証
   - 年シート・月行・カテゴリ列を特定
   - 既存値に新規金額を加算

8. **結果表示** (`GET /result`)
   - 月別・カテゴリ別サマリー
   - ChatGPT分類結果サマリー（NEW）
   - 未登録店舗リスト（残存分）
   - 処理詳細ログ

---

## エンドポイント詳細

### POST /gpt/classify

**セキュリティ**: CSRF保護、セッション検証

#### リクエスト
```json
{
  "unregistered_stores": [
    {"store": "スターバックス", "amount": 560, "count": 3},
    {"store": "イオンリテール", "amount": 1234, "count": 1}
  ]
}
```

**バリデーション**:
- `unregistered_stores`: 必須、配列形式
- `store`: 必須、文字列（最大255文字）
- `amount`: 必須、数値
- `count`: 必須、正の整数

#### レスポンス（成功時）
```json
{
  "status": "success",
  "data": {
    "classifications": [
      {"store": "スターバックス", "category": "外食費", "column": "D"},
      {"store": "イオンリテール", "category": "食材費", "column": "C"}
    ]
  }
}
```

#### レスポンス（エラー時）
```json
{
  "status": "error",
  "message": "ChatGPT API failed, using default category",
  "data": {
    "classifications": [
      {"store": "スターバックス", "category": "雑貨費", "column": "H"},
      {"store": "イオンリテール", "category": "雑貨費", "column": "H"}
    ]
  }
}
```

---

### GET /gpt/classification

**セキュリティ**: セッション検証

#### レスポンス
ChatGPT分類結果確認画面（gpt_classification.html）を表示

**セッションデータ要件**:
- `gpt_classifications`: ChatGPT分類結果（必須）
- `unregistered_stores_detail`: 未登録店舗詳細（必須）

#### 画面内容
- ChatGPT分類結果一覧テーブル
  - 店舗名
  - 分類結果（カテゴリ、列）
  - 金額
  - 出現回数
  - 編集ボタン（ドロップダウン）
- 確定ボタン（`POST /gpt/confirm`）
- キャンセルボタン（`POST /gpt/cancel`）

---

### POST /gpt/confirm

**セキュリティ**: CSRF保護、セッション検証、入力バリデーション

#### リクエスト
```json
{
  "classifications": [
    {"store": "スターバックス", "category": "外食費", "column": "D"},
    {"store": "イオンリテール", "category": "食材費", "column": "C"}
  ]
}
```

**バリデーション**:
- `classifications`: 必須、配列形式
- `store`: 必須、文字列（最大255文字）
- `category`: 必須、文字列（最大50文字）
- `column`: 必須、C～V列の範囲チェック（A1形式列番号）

#### レスポンス（成功時）
```json
{
  "status": "success",
  "message": "Classifications saved to database",
  "data": {
    "saved_count": 2,
    "failed_count": 0
  }
}
```

#### レスポンス（エラー時）
```json
{
  "status": "error",
  "message": "Database write failed",
  "data": {
    "saved_count": 1,
    "failed_count": 1,
    "failed_stores": ["イオンリテール"]
  }
}
```

---

### POST /gpt/cancel

**セキュリティ**: CSRF保護、セッション検証

#### リクエスト
リクエストボディなし（セッションクリアのみ）

#### レスポンス
```json
{
  "status": "success",
  "message": "Classification cancelled"
}
```

**処理内容**:
- セッションから`gpt_classifications`を削除
- セッションから`unregistered_stores_detail`を削除
- リダイレクト先: `/result`

---

## レスポンス形式

### 成功時（JSON）
```json
{
  "status": "success",
  "data": {
    "summary": {
      "total_amount": 27575,
      "total_count": 17,
      "by_category": {...}
    },
    "gpt_classification_summary": {
      "classified_stores": 10,
      "total_amount": 5680,
      "failed_count": 0
    },
    "unregistered_stores": [...]
  }
}
```

### エラー時（JSON）
```json
{
  "status": "error",
  "message": "エラー内容",
  "code": "ERROR_CODE",
  "details": "詳細なエラー情報"
}
```

---

## エラーコード一覧

| コード | 説明 | 対処法 |
|-------|------|--------|
| CSV_PARSE_ERROR | CSV解析失敗 | ファイル形式・エンコーディングを確認 |
| GPT_API_ERROR | ChatGPT API失敗 | デフォルトカテゴリで続行、APIキー確認 |
| GPT_VALIDATION_ERROR | ChatGPT分類入力検証エラー | 列番号C-V範囲、カテゴリ名50文字以内を確認 |
| DB_WRITE_ERROR | SQLite書き込み失敗 | データベースファイル権限確認 |
| SHEETS_API_ERROR | Google Sheets API失敗 | 認証情報・権限確認 |
| INVALID_REQUEST | 無効なリクエスト | リクエストパラメータ確認 |
| CSRF_ERROR | CSRFトークン検証失敗 | ページ再読み込み、セッション確認 |
| SESSION_ERROR | セッションデータ不正 | セッションタイムアウト、ページ再読み込み |

---

## セキュリティ要件

### 認証情報管理
- OpenAI API Key: 環境変数`OPENAI_API_KEY`で管理（`.env`、`.gitignore`対象）
- Google Service Account Key: `config/service_account.json`（`.gitignore`対象）

### レート制限
- ChatGPT API: 最大50件/リクエスト、exponential backoff でリトライ
- Google Sheets API: batchUpdate使用、1秒あたり10リクエスト制限

### データ検証
- CSVファイルサイズ上限: 10MB（環境変数`CSV_MAX_FILE_SIZE`で調整可能）
- 未登録店舗数上限: 100件/回（超過時は分割処理）

---

## パフォーマンス目標

| エンドポイント | レスポンス時間 | スループット |
|--------------|--------------|-------------|
| POST /upload | < 2秒 | 10MB/2秒 |
| POST /preview | < 1秒 | 1000件/1秒 |
| POST /gpt/classify | < 10秒 | 50件/10秒 |
| POST /gpt/confirm | < 2秒 | 100件/2秒 |
| POST /process | < 30秒 | 1000件/30秒 |

---

## ダウンロード方法

このファイルをダウンロードするには、以下の手順で操作してください：

1. このテキスト全体を選択してコピー
2. テキストエディタに貼り付け
3. ファイル名を `backend_api_routes.md` として保存

または、ブラウザの「名前を付けて保存」機能をご利用ください。
