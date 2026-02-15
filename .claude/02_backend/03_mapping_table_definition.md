# マッピングテーブル定義書

## 概要
店舗名とカテゴリ・列番号の対応関係を管理するテーブル。**SQLite**形式で`data/mappings.db`に保存。
**移行方針**: 従来のJSON形式（`config/mapping.json`）から、データベース管理に移行。

## ストレージ形式の変更履歴

| バージョン | ストレージ形式 | ファイルパス | 備考 |
|----------|-------------|------------|------|
| v1.0 | JSON | config/mapping.json | 初期実装 |
| v2.0 | SQLite | data/mappings.db | ChatGPT分類フロー対応、JSON形式から移行 |

---

## 1. store_mappings テーブル（メインテーブル）

### テーブル定義

| カラム名 | データ型 | NOT NULL | DEFAULT | 説明 | 例 |
|---------|---------|---------|---------|-----|-----|
| id | INTEGER | ○ | PRIMARY KEY AUTOINCREMENT | マッピングID | 1 |
| store | TEXT | ○ | - | 店舗名（完全一致検索用） | "ユシンヤカマタテン" |
| pattern | TEXT | - | NULL | 店舗名パターン（部分一致検索用） | "ユシンヤ" |
| match_type | TEXT | ○ | 'contains' | 一致方法 | "contains" |
| category | TEXT | ○ | - | カテゴリ名 | "外食費" |
| column | TEXT | ○ | - | 列番号（C～V） | "D" |
| priority | INTEGER | ○ | 4 | 優先順位（1=最高、4=ChatGPT自動分類） | 1 |
| source | TEXT | ○ | 'manual' | データソース | "auto" / "manual" |
| created_at | TIMESTAMP | ○ | CURRENT_TIMESTAMP | 登録日時 | "2025-08-15 10:30:00" |
| updated_at | TIMESTAMP | - | NULL | 最終更新日時 | "2025-08-16 14:20:00" |
| note | TEXT | - | NULL | 備考 | - |

### SQLスキーマ定義
```sql
CREATE TABLE IF NOT EXISTS store_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store TEXT NOT NULL,
    pattern TEXT,
    match_type TEXT NOT NULL DEFAULT 'contains',
    category TEXT NOT NULL,
    column TEXT NOT NULL CHECK(length(column) = 1 AND column BETWEEN 'B' AND 'V'),
    priority INTEGER NOT NULL DEFAULT 4 CHECK(priority BETWEEN 1 AND 5),
    source TEXT NOT NULL DEFAULT 'manual' CHECK(source IN ('manual', 'auto')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    note TEXT
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_store_mappings_store ON store_mappings(store);
CREATE INDEX IF NOT EXISTS idx_store_mappings_pattern ON store_mappings(pattern);
CREATE INDEX IF NOT EXISTS idx_store_mappings_category ON store_mappings(category);
CREATE INDEX IF NOT EXISTS idx_store_mappings_priority ON store_mappings(priority);
CREATE INDEX IF NOT EXISTS idx_store_mappings_source ON store_mappings(source);
```

### match_type の値

| 値 | 説明 | 使用例 |
|-----|------|-------|
| exact | 完全一致 | "セブンイレブン新宿店" = "セブンイレブン新宿店" |
| startswith | 前方一致 | "セブンイレブン..." で始まる店舗名 |
| contains | 部分一致 | "...セブン..." を含む店舗名 |
| keyword | キーワード一致 | "セブン" OR "イレブン" を含む |

### priority の値

| 優先順位 | 値 | 説明 | source |
|---------|---|------|--------|
| 最高 | 1 | 手動で明示的に設定した最優先マッピング | manual |
| 高 | 2 | 手動で設定した優先マッピング | manual |
| 中 | 3 | 手動で設定した通常マッピング | manual |
| 低 | 4 | ChatGPT自動分類で登録されたマッピング | auto |
| 最低 | 5 | （廃止: ユーザー確認画面で設定） | - |

### source の値

| 値 | 説明 | 登録方法 |
|-----|------|---------|
| manual | 手動登録 | Web UIから手動で追加・編集 |
| auto | 自動登録 | ChatGPT分類フローで自動登録 |

---

## 2. unregistered_stores テーブル（任意：未登録店舗管理用）

### テーブル定義

| カラム名 | データ型 | NOT NULL | DEFAULT | 説明 | 例 |
|---------|---------|---------|---------|-----|-----|
| id | INTEGER | ○ | PRIMARY KEY AUTOINCREMENT | レコードID | 1 |
| store | TEXT | ○ | - | 未登録店舗名 | "新規店舗A" |
| first_seen_date | DATE | ○ | - | 初回検出日 | "2025-08-15" |
| last_seen_date | DATE | ○ | - | 最終検出日 | "2025-08-16" |
| occurrence_count | INTEGER | ○ | 1 | 出現回数 | 5 |
| total_amount | INTEGER | ○ | 0 | 合計金額 | 15000 |
| status | TEXT | ○ | 'pending' | ステータス | "pending" / "classified" / "ignored" |
| created_at | TIMESTAMP | ○ | CURRENT_TIMESTAMP | 登録日時 | "2025-08-15 10:30:00" |
| updated_at | TIMESTAMP | - | NULL | 最終更新日時 | "2025-08-16 14:20:00" |

### SQLスキーマ定義
```sql
CREATE TABLE IF NOT EXISTS unregistered_stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store TEXT NOT NULL UNIQUE,
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    total_amount INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'classified', 'ignored')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_unregistered_stores_store ON unregistered_stores(store);
CREATE INDEX IF NOT EXISTS idx_unregistered_stores_status ON unregistered_stores(status);
CREATE INDEX IF NOT EXISTS idx_unregistered_stores_last_seen ON unregistered_stores(last_seen_date);
```

### status の値

| 値 | 説明 |
|-----|------|
| pending | 未分類（ChatGPT分類待ち） |
| classified | 分類済み（store_mappingsに登録済み） |
| ignored | 無視（分類不要） |

---

## マッチング処理順序

1. **完全一致（exact）** - priority昇順
2. **前方一致（startswith）** - priority昇順
3. **部分一致（contains）** - priority昇順
4. **キーワード一致（keyword）** - priority昇順
5. **未登録** → ユーザー確認画面で手動設定

**優先順位の適用**:
- 同じmatch_typeの場合、priorityが**小さい**ものを優先
- 例: priority=1（手動設定）> priority=4（ChatGPT自動分類）

---

## データ移行

### JSON → SQLite 移行スクリプト例
```python
import json
import sqlite3
from datetime import datetime

def migrate_json_to_sqlite(json_path, db_path):
    """JSONマッピングデータをSQLiteに移行"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for mapping in data.get('mappings', []):
        cursor.execute('''
            INSERT INTO store_mappings (store, pattern, match_type, category, column, priority, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            mapping.get('pattern'),  # store
            mapping.get('pattern'),  # pattern
            mapping.get('match_type', 'contains'),
            mapping.get('category'),
            mapping.get('column'),
            mapping.get('priority', 3),  # 既存データは手動設定として priority=3
            'manual'
        ))

    conn.commit()
    conn.close()
```

---

## 運用方法

### データ管理
- **手動登録**: Web UIから追加・編集・削除
- **自動登録**: ChatGPT分類フローで自動追加（source='auto', priority=4）
- **バックアップ**: 定期的にSQLiteファイルをバックアップ（`data/backups/`）

### パフォーマンス最適化
- インデックスによる高速検索
- トランザクション処理によるデータ整合性保証
- バッチ更新によるChatGPT分類結果の一括登録

### エクスポート・インポート
- JSON形式へのエクスポート機能（互換性維持）
- 他環境からのインポート機能

---

## 関連ドキュメント
- [カテゴリマスタ定義](./04_category_master_definition.md)
- [バックエンドモジュール仕様](./02_backend_modules_spec.md)
- [データフロー](../01_development_docs/03_data_flow.md)