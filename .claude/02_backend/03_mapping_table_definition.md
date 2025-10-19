# マッピングテーブル定義書

## 概要
店舗名とカテゴリ・列番号の対応関係を管理するテーブル。JSON形式で`config/mapping.json`に保存。

## データ構造

| フィールド名 | 型 | 必須 | 説明 | 例 |
|------------|-----|------|------|-----|
| id | integer | ○ | マッピングID | 1 |
| pattern | string | ○ | 店舗名パターン | "ユシンヤ" |
| match_type | string | ○ | 一致方法 | "contains" |
| category | string | ○ | カテゴリ名 | "外食費" |
| column | string | ○ | 列番号（B～V） | "C" |
| priority | integer | ○ | 優先順位（1=最高） | 1 |
| note | string | - | 備考 | - |

## match_type の値

| 値 | 説明 |
|-----|------|
| exact | 完全一致 |
| startswith | 前方一致 |
| contains | 部分一致 |
| keyword | キーワード一致 |

## JSON構造例
```json
{
  "version": "1.0",
  "mappings": [
    {
      "id": 1,
      "pattern": "ユシンヤ",
      "match_type": "contains",
      "category": "外食費",
      "column": "C",
      "priority": 1
    },
    {
      "id": 2,
      "pattern": "AMAZON",
      "match_type": "contains",
      "category": "日用品費",
      "column": "D",
      "priority": 1
    }
  ],
  "default": {
    "category": "支払額",
    "column": "B",
    "note": "未分類はB列に振り分け"
  }
}
```

## インデックス
- PRIMARY KEY: id
- INDEX: pattern（検索用）
- INDEX: category（カテゴリ別検索用）

## マッチング処理順序
1. 完全一致（exact）
2. 前方一致（startswith）
3. 部分一致（contains）
4. キーワード一致（keyword）
5. デフォルト列（B列）

## 運用
- 手動編集可能（JSON直接編集）
- Web UIからの追加・編集・削除対応
- インポート・エクスポート機能あり