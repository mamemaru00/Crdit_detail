# 設定テーブル定義書

## 概要
システム設定を管理するテーブル。将来的にデータベース化する際の定義。現在はJSON/環境変数で管理。

## データ構造

| フィールド名 | 型 | 必須 | 説明 | デフォルト値 |
|------------|-----|------|------|------------|
| spreadsheet_id | string | ○ | スプレッドシートID | - |
| default_year | integer | ○ | デフォルト対象年 | 2025 |
| default_column | string | ○ | デフォルト列 | "B" |
| encoding | string | ○ | CSV文字コード | "Shift_JIS" |
| auto_register | boolean | - | 自動登録フラグ | false |
| backup_enabled | boolean | - | バックアップ有効 | false |
| log_level | string | - | ログレベル | "INFO" |
| api_timeout | integer | - | API タイムアウト（秒） | 30 |
| batch_size | integer | - | バッチ更新サイズ | 100 |

## 設定値の詳細

### spreadsheet_id
- Googleスプレッドシートの一意識別子
- URL末尾の文字列
- 例：`10RJcB-_pOqsxA-6mGZ...`

### default_year
- CSV処理時の対象年
- ユーザー選択可能
- 範囲：2020～2030

### default_column
- 未登録店舗の振り分け先
- 値：B～V
- 通常はB列（支払額）

### encoding
- CSVファイルの文字コード
- 自動検出も可能
- サポート：Shift_JIS, UTF-8, CP932

### auto_register
- 未登録店舗の自動マッピング登録
- true: 自動登録、false: 手動確認

### backup_enabled
- マッピングテーブルの自動バックアップ
- true: 更新時にバックアップ作成

### log_level
- システムログの出力レベル
- 値：DEBUG, INFO, WARNING, ERROR

### api_timeout
- Google Sheets API接続タイムアウト
- 単位：秒
- 推奨：30～60秒

### batch_size
- スプレッドシート一括更新の件数
- 大きすぎるとAPI制限に抵触
- 推奨：50～200

## JSON設定ファイル例

```json
{
  "spreadsheet_id": "10RJcB-_pOqsxA-6mGZ...",
  "default_year": 2025,
  "default_column": "B",
  "encoding": "Shift_JIS",
  "auto_register": false,
  "backup_enabled": true,
  "log_level": "INFO",
  "api_timeout": 30,
  "batch_size": 100
}
```

## 環境変数での管理

```bash
SPREADSHEET_ID=10RJcB-_pOqsxA-6mGZ...
DEFAULT_YEAR=2025
DEFAULT_COLUMN=B
CSV_ENCODING=Shift_JIS
AUTO_REGISTER=false
BACKUP_ENABLED=true
LOG_LEVEL=INFO
API_TIMEOUT=30
BATCH_SIZE=100
```

## データベース化時のテーブル設計

```sql
CREATE TABLE config (
  key VARCHAR(50) PRIMARY KEY,
  value TEXT NOT NULL,
  description TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 運用方針
- 現在：JSON/環境変数で管理
- 将来：SQLiteまたはPostgreSQLで管理
- 変更時：アプリケーション再起動不要（リロード機能実装予定）