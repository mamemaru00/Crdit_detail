# 処理結果サマリー定義書

## 概要
CSV処理結果の集計データ。APIレスポンスとして返却され、画面表示に使用。

## データ構造

| フィールド名 | 型 | 必須 | 説明 |
|------------|-----|------|------|
| total_amount | integer | ○ | 合計金額 |
| total_count | integer | ○ | 処理件数 |
| year | integer | ○ | 対象年 |
| month | integer | ○ | 対象月 |
| by_category | object | ○ | カテゴリ別集計 |
| unregistered_stores | array | ○ | 未登録店舗リスト |
| processed_at | datetime | ○ | 処理日時 |

## by_category オブジェクト構造

| フィールド名 | 型 | 説明 |
|------------|-----|------|
| category_name | string | カテゴリ名 |
| column | string | 列番号 |
| amount | integer | 合計金額 |
| count | integer | 件数 |

## unregistered_stores 配列構造

| フィールド名 | 型 | 説明 |
|------------|-----|------|
| store_name | string | 店舗名 |
| amount | integer | 金額 |

## JSON レスポンス例

```json
{
  "total_amount": 27575,
  "total_count": 17,
  "year": 2025,
  "month": 8,
  "by_category": {
    "外食費": {
      "column": "C",
      "amount": 11560,
      "count": 8
    },
    "日用品費": {
      "column": "D",
      "amount": 7045,
      "count": 5
    },
    "娯楽費": {
      "column": "G",
      "amount": 3100,
      "count": 3
    },
    "交通費": {
      "column": "N",
      "amount": 5870,
      "count": 1
    }
  },
  "unregistered_stores": [
    {
      "store_name": "デイーエムエム",
      "amount": 300
    },
    {
      "store_name": "ル－プ",
      "amount": 143
    }
  ],
  "processed_at": "2025-10-19T12:34:56"
}
```

## 使用用途

### 画面表示
- 月別・カテゴリ別の加算額表示
- 処理件数の表示
- 未登録店舗の一覧表示

### ログ出力
- 処理結果の記録
- エラー発生時の調査資料

## エラー時のレスポンス

```json
{
  "status": "error",
  "message": "エラー内容",
  "code": "ERROR_CODE"
}
```

## 注意事項
- 金額は整数型（円単位）
- 日時はISO 8601形式
- 未登録店舗は必ず配列で返却（空配列含む）