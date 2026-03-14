# 外部APIレスポンスのデータ型ハンドリングルール

## 概要

外部API（Google Sheets API 等）のレスポンスに含まれるセル値を数値変換する際、
ロケール依存のフォーマット済み文字列（例: `￥8,035`）が返ることがある。
これを直接 `float()` に渡すと `ValueError` が発生し、サイレントフォールバックで
`0.0` が書き込まれ、既存データを破壊するバグを引き起こす。

本ルールは Issue #87 の根本原因分析に基づき、同種のバグを再発させないための
コーディング規約を定める。

---

## 背景（Issue #87）

### 問題の経緯

1. Google Sheets APIの `batch_get()` を呼び出した際、セルのフォーマット設定が
   「通貨（日本円）」になっていると、数値 `8035` ではなくフォーマット済み文字列
   `￥8,035`（全角円記号 + カンマ区切り）が返却されることがある。

2. このレスポンス値を直接 `float("￥8,035")` に渡すと `ValueError` が発生する。

3. 当時の実装では `ValueError` を `except` でキャッチして `0.0` を返す
   フォールバック処理が組まれていたため、エラーは表面化せず `0.0` がそのまま
   スプレッドシートに書き込まれた。

4. その結果、既存の積み上げ金額（例: `8,035円`）が `0.0` に上書きされ、
   家計簿データが消失する致命的なデータ破壊が発生した。

### 根本原因

「外部APIが返す値のデータ型・フォーマットは、呼び出し側が期待する型と
一致するとは限らない」という前提を欠いたまま、APIレスポンスを直接
型変換に渡していたこと。

### 関連コミット

| コミット | 内容 |
|---------|------|
| `7c75fd4` | `_parse_cell_value()` ヘルパー関数追加。`get_cell_value()` と `batch_update_cells()` の `float()` 直接呼び出しを置換 |
| `d2fccfb` | `batch_get()` に `value_render_option='UNFORMATTED_VALUE'` を追加。全角円記号（`￥` U+FF05）の除去を追加 |

---

## ルール 1: 外部APIレスポンスのデータ型を信頼しない

### 原則

外部API（Google Sheets API、OpenAI API 等）から受け取った値を数値に変換する際、
**値の型・フォーマットが事前に保証されているとは考えてはならない**。

### 禁止事項

```python
# 禁止: APIレスポンスを直接 float() に渡す
cell_value = worksheet.cell(row, col).value
value = float(cell_value)  # NG: "￥8,035" が来たときに ValueError

# 禁止: ValueError のサイレントキャッチで 0.0 を返す
try:
    value = float(cell_value)
except ValueError:
    value = 0.0  # NG: エラーを握り潰してデータ破壊を隠蔽
```

### 推奨事項

```python
# 推奨: _parse_cell_value() を経由して安全に変換する
from modules.sheets_api import _parse_cell_value

cell_value = worksheet.cell(row, col).value
value = _parse_cell_value(cell_value)  # OK: 通貨記号・カンマを除去してから変換
```

---

## ルール 2: 数値変換には `_parse_cell_value()` を使用する

### 定義（`modules/sheets_api.py` L394-425）

`_parse_cell_value(value) -> float` は、スプレッドシートのセル値を安全に
`float` へ変換するヘルパー関数。以下を処理する。

| 入力値の種類 | 処理内容 |
|------------|---------|
| `None`、`""`、空白文字列 | `0.0` を返す（空セル扱い） |
| `int`、`float` | `float()` に直接渡す（安全） |
| 通貨フォーマット文字列 `¥8,035` | 半角円記号・カンマ・バックスラッシュを除去後 `float()` へ |
| 通貨フォーマット文字列 `￥8,035` | 全角円記号（U+FF05）・カンマを除去後 `float()` へ |
| 変換不可の文字列 | `WARNING` ログを出力し `0.0` を返す |

### 使用必須の状況

- `worksheet.cell(row, col).value` の結果を数値として使う場合
- `batch_get()` のレスポンスから個々のセル値を取り出して数値として使う場合
- Google Sheets APIのレスポンス全般で数値変換を行う場合

### 変換失敗時のログ確認

`_parse_cell_value()` は変換失敗時に `WARNING` レベルのログを出力する。

```
[CELL:PARSE] セル値の数値変換に失敗: 'XXX' → 0.0
```

このログが出力されている場合、スプレッドシートのセルフォーマットまたは
APIのレスポンス形式を確認すること。`0.0` への無音フォールバックは
データ破壊につながる可能性がある。

---

## ルール 3: `batch_get()` には `UNFORMATTED_VALUE` を標準使用する

### 原則

`worksheet.batch_get()` を呼び出す際は、常に
`value_render_option='UNFORMATTED_VALUE'` を指定すること。

### 理由

`value_render_option` を省略（デフォルト: `FORMATTED_VALUE`）した場合、
セルに「通貨」フォーマットが設定されていると数値でなく
ロケール依存の文字列（`￥8,035` 等）が返却される。

`UNFORMATTED_VALUE` を指定することで、フォーマット設定に依存せず
常に数値として取得できる。

### 必須コード例

```python
# 正しい書き方: UNFORMATTED_VALUE を指定する
batch_result = worksheet.batch_get(
    [range_name],
    value_render_option='UNFORMATTED_VALUE'
)

# 禁止: value_render_option を省略する
batch_result = worksheet.batch_get([range_name])  # NG: FORMATTED_VALUE が返る場合がある
```

### 対象メソッド

| メソッド | 対応 |
|---------|------|
| `worksheet.batch_get()` | `value_render_option='UNFORMATTED_VALUE'` を必ず指定 |
| `worksheet.get()` | 同様に `value_render_option='UNFORMATTED_VALUE'` を指定 |
| `worksheet.cell().value` | `UNFORMATTED_VALUE` オプション非対応。取得値は `_parse_cell_value()` で変換 |

---

## ルール 4: 空セルと変換失敗を区別する

### 問題の背景

`0.0` は「空セル」を意味する場合と「変換失敗のフォールバック」を意味する場合がある。
これらを区別しないと、変換失敗が空セルとして誤認識され、
既存データが `0.0` で上書きされるリスクがある。

### 判断基準

| 状況 | 期待される挙動 |
|-----|-------------|
| セル値が `None` または空文字 | `0.0` を返す（正常ケース。加算時は現在値 `0` として扱う） |
| 数値として有効な値（`int`、`float`、`"1234"` 等） | 変換後の値を返す |
| 通貨フォーマット文字列（`"¥8,035"`、`"￥8,035"` 等） | 数値部分を抽出して返す |
| 解釈不能な文字列 | `WARNING` ログを出力して `0.0` を返す。**その後の書き込みを中止すべきか検討すること** |

### 実装指針

変換失敗の `0.0` フォールバックをそのままスプレッドシートに書き込む実装は避けること。
必要であれば呼び出し元で `WARNING` ログの有無を確認するか、
変換失敗を示す別の戻り値（例: `None`）を使用して書き込みをスキップする処理を追加すること。

---

## ルール 5: `get_cell_value()` の制約を理解して使用する

### 制約事項

`get_cell_value()` は内部で `worksheet.cell(row, col).value` を使用しているため、
**`UNFORMATTED_VALUE` オプションが適用されない**。

この制約により、セルに通貨フォーマットが設定されている場合、
引き続きフォーマット済み文字列が返ってくる可能性がある。

### 現在の対策

`get_cell_value()` は内部で `_parse_cell_value()` を呼び出しているため、
通貨フォーマット文字列であっても正しく数値変換できる。

### 使い分け指針

| 利用シーン | 推奨メソッド |
|-----------|------------|
| 複数セルを一括取得してパフォーマンスを重視する場合 | `batch_get()` + `value_render_option='UNFORMATTED_VALUE'` |
| 単一セルを取得する場合 | `get_cell_value()`（内部で `_parse_cell_value()` 呼び出し済み） |
| 単一セルを `worksheet.cell()` で直接取得する場合 | 必ず `_parse_cell_value()` で変換 |

---

## Issue #87 教訓サマリー

| 観点 | 教訓 |
|-----|-----|
| データ型の仮定 | APIレスポンスの型は仕様書通りとは限らない。ロケールやセルフォーマット設定に依存する場合がある |
| サイレントフォールバック | `except ValueError: return 0.0` のような握り潰しは、データ破壊を隠蔽する危険な実装パターン |
| フォーマット設定の影響 | Google Sheetsのセルフォーマット設定は、APIレスポンスの値の形式に影響する |
| テスト用データ | テストデータには、実際のスプレッドシートで発生しうる通貨フォーマット文字列を含めること |
| UNFORMATTED_VALUE | `batch_get()` では常に `UNFORMATTED_VALUE` を指定することで根本的に問題を回避できる |

---

## チェックリスト（コードレビュー時）

Google Sheets APIと連携するコードをレビューする際は、以下を確認すること。

- [ ] `batch_get()` に `value_render_option='UNFORMATTED_VALUE'` が指定されているか
- [ ] セル値の `float()` 直接変換が存在しないか
- [ ] `_parse_cell_value()` を経由して数値変換しているか
- [ ] `ValueError` / `TypeError` をサイレントキャッチして `0.0` を返す実装になっていないか
- [ ] 変換失敗のフォールバック値（`0.0`）をそのまま書き込む実装になっていないか
- [ ] 新規テストコードに通貨フォーマット文字列（`¥1,000`、`￥1,000`）のテストケースが含まれているか
