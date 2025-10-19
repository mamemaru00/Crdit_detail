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
GET  /mapping/list            # マッピング一覧をJSON取得
POST /mapping/add             # 新規マッピング追加
PUT  /mapping/edit/<id>       # マッピング編集
DELETE /mapping/delete/<id>   # マッピング削除
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

## データフロー

1. **CSVアップロード** (`POST /upload`)
   - Shift_JIS → UTF-8 変換
   - ファイル保存

2. **CSV解析** (`POST /preview`)
   - 明細データ抽出（6桁日付の行）
   - YYMMDD → YYYY/MM/DD 変換
   - プレビュー5件返却

3. **カテゴリ判定** (`POST /process`)
   - 各店舗名をマッピングテーブルで照合
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

## レスポンス形式

**成功時（JSON）**
```json
{
  "status": "success",
  "data": {
    "summary": {
      "total_amount": 27575,
      "total_count": 17,
      "by_category": {...}
    },
    "unregistered_stores": [...]
  }
}
```

**エラー時（JSON）**
```json
{
  "status": "error",
  "message": "エラー内容",
  "code": "ERROR_CODE"
}
```

---

## ダウンロード方法

このファイルをダウンロードするには、以下の手順で操作してください：

1. このテキスト全体を選択してコピー
2. テキストエディタに貼り付け
3. ファイル名を `backend_api_routes.md` として保存

または、ブラウザの「名前を付けて保存」機能をご利用ください。# バックエンドAPIルート設計

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
GET  /mapping/list            # マッピング一覧をJSON取得
POST /mapping/add             # 新規マッピング追加
PUT  /mapping/edit/<id>       # マッピング編集
DELETE /mapping/delete/<id>   # マッピング削除
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

## データフロー

1. **CSVアップロード** (`POST /upload`)
   - Shift_JIS → UTF-8 変換
   - ファイル保存

2. **CSV解析** (`POST /preview`)
   - 明細データ抽出（6桁日付の行）
   - YYMMDD → YYYY/MM/DD 変換
   - プレビュー5件返却

3. **カテゴリ判定** (`POST /process`)
   - 各店舗名をマッピングテーブルで照合
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

## レスポンス形式

**成功時（JSON）**
```json
{
  "status": "success",
  "data": {
    "summary": {
      "total_amount": 27575,
      "total_count": 17,
      "by_category": {...}
    },
    "unregistered_stores": [...]
  }
}
```

**エラー時（JSON）**
```json
{
  "status": "error",
  "message": "エラー内容",
  "code": "ERROR_CODE"
}
```

---

## ダウンロード方法

このファイルをダウンロードするには、以下の手順で操作してください：

1. このテキスト全体を選択してコピー
2. テキストエディタに貼り付け
3. ファイル名を `backend_api_routes.md` として保存

または、ブラウザの「名前を付けて保存」機能をご利用ください。