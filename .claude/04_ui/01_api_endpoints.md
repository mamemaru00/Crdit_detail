# APIエンドポイント

## 8.1 主要エンドポイント一覧

### 8.1.1 画面表示系

| メソッド | エンドポイント | 説明 | レスポンス |
|---------|---------------|------|-----------|
| GET | `/` | メイン画面表示 | HTML |
| GET | `/mapping` | マッピング管理画面 | HTML |
| GET | `/unregistered` | 未登録店舗確認画面 | HTML |

### 8.1.2 CSV処理系

| メソッド | エンドポイント | 説明 | リクエスト | レスポンス |
|---------|---------------|------|-----------|-----------|
| POST | `/api/upload` | CSVアップロード | multipart/form-data | JSON |
| POST | `/api/preview` | CSVプレビュー取得 | file: File | JSON |
| POST | `/api/execute` | スプレッドシート取込実行 | spreadsheet_id, year, file | JSON |

**リクエスト例（/api/execute）:**
```json
{
  "spreadsheet_id": "1ABC...xyz",
  "year": "2024",
  "file": "data.csv"
}
```

**レスポンス例:**
```json
{
  "success": true,
  "summary": {
    "total_amount": 50000,
    "total_count": 25,
    "by_month": {
      "2024-01": {"日用品": 15000, "食費": 8000}
    }
  },
  "unregistered": [
    {"store": "新規店舗A", "amount": 2000}
  ]
}
```

### 8.1.3 マッピング管理系

| メソッド | エンドポイント | 説明 | リクエスト | レスポンス |
|---------|---------------|------|-----------|-----------|
| GET | `/api/mappings` | マッピング一覧取得 | query: search | JSON |
| POST | `/api/mappings` | マッピング新規登録 | JSON | JSON |
| PUT | `/api/mappings/<id>` | マッピング更新 | JSON | JSON |
| DELETE | `/api/mappings/<id>` | マッピング削除 | - | JSON |
| POST | `/api/mappings/import` | マッピング一括登録 | JSON/CSV | JSON |
| GET | `/api/mappings/export` | マッピング出力 | format: json/csv | File |

**リクエスト例（POST /api/mappings）:**
```json
{
  "pattern": "セブンイレブン",
  "match_type": "前方一致",
  "category": "日用品",
  "column": "B"
}
```

### 8.1.4 未登録店舗処理系

| メソッド | エンドポイント | 説明 | リクエスト | レスポンス |
|---------|---------------|------|-----------|-----------|
| POST | `/api/unregistered/apply` | 未登録店舗振り分け | JSON | JSON |
| POST | `/api/unregistered/register` | 未登録店舗をマッピング登録 | JSON | JSON |

**リクエスト例（/api/unregistered/apply）:**
```json
{
  "stores": [
    {
      "name": "新規店舗A",
      "category": "日用品",
      "column": "B",
      "save_mapping": true
    }
  ]
}
```