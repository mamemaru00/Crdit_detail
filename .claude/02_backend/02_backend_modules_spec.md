# バックエンドモジュール仕様

## 1. CSV解析モジュール（csv_parser.py）

### 主要機能
- Shift_JISエンコーディングの自動検出・変換
- YYMMDD形式からYYYY/MM/DD形式への日付変換
- 明細データ抽出（6桁数字で始まる行）
- 月別グループ化

### 主要メソッド
```python
def parse_csv(file_path: str) -> List[Dict]:
    """CSVファイルを解析して明細データを返す"""
    
def detect_encoding(file_path: str) -> str:
    """文字コードを自動検出"""
    
def convert_date(yymmdd: str) -> datetime:
    """YYMMDD形式をdatetime型に変換"""
    
def extract_records(csv_data: DataFrame) -> List[Dict]:
    """明細行を抽出"""
```

### データ変換例
```python
# 入力
"250815,本人,ユシンヤカマタテン,１回,,,5780,,"

# 出力
{
    "date": "2025-08-15",
    "month": 8,
    "year": 2025,
    "store": "ユシンヤカマタテン",
    "amount": 5780,
    "user": "本人",
    "payment_method": "１回"
}
```

## 2. カテゴリ判定モジュール（category_matcher.py）

### 主要機能
- マッピングテーブル読み込み（JSON）
- 店舗名パターンマッチング（完全一致/前方一致/部分一致）
- 優先順位付き判定
- 未登録店舗の検出

### 主要メソッド
```python
def load_mapping(config_path: str) -> Dict:
    """マッピングテーブルを読み込む"""
    
def match_category(store_name: str, mappings: List[Dict]) -> Dict:
    """店舗名からカテゴリと列番号を判定"""
    
def find_best_match(store_name: str, patterns: List[Dict]) -> Dict:
    """優先順位に基づき最適なマッピングを返す"""
    
def get_unregistered_stores(records: List[Dict]) -> List[str]:
    """未登録店舗のリストを返す"""
```

### マッチングロジック
```
1. 完全一致チェック
2. 前方一致チェック
3. 部分一致チェック
4. キーワード一致チェック
5. デフォルト列（B列）に振り分け
```

## 3. Google Sheets連携モジュール（sheets_client.py）

### 主要機能
- サービスアカウント認証
- スプレッドシート接続
- 年シート・月行・カテゴリ列の特定
- セル値の読み書き
- バッチ更新

### 主要メソッド
```python
def authenticate(credentials_path: str) -> gspread.Client:
    """サービスアカウントで認証"""

def open_spreadsheet(client: Client, sheet_id: str) -> Spreadsheet:
    """スプレッドシートを開く"""

def get_year_sheet(spreadsheet: Spreadsheet, year: int) -> Worksheet:
    """年シートを取得"""

def update_cell(sheet: Worksheet, row: int, col: str, value: float):
    """セル値を更新（加算）"""

def batch_update(sheet: Worksheet, updates: List[Dict]):
    """複数セルを一括更新"""
```

### 更新ロジック
```python
# 行番号計算
row = 3 + month  # ヘッダー3行 + 月番号

# 既存値取得
current_value = sheet.cell(row, column).value or 0

# 新値計算
new_value = current_value + amount

# 更新実行
sheet.update_cell(row, column, new_value)
```

---

## 4. ChatGPT分類モジュール（gpt_classifier.py）【NEW】

### 主要機能
- 未登録店舗の自動カテゴリ分類
- OpenAI GPT-5 API 連携
- カテゴリマスタの動的送信
- エラーハンドリング（API失敗時のフォールバック）
- レート制限対応

### 主要メソッド
```python
def classify_unregistered_stores(
    unregistered_stores: List[Dict],
    category_master: Dict[str, str]
) -> List[Dict]:
    """
    未登録店舗をChatGPTで分類

    Args:
        unregistered_stores: 未登録店舗リスト
            [{"store": "店舗名", "amount": 金額, "count": 出現回数}, ...]
        category_master: カテゴリマスタ
            {"C": "食材費", "D": "外食費", ...}

    Returns:
        分類結果リスト
            [{"store": "店舗名", "category": "カテゴリ名", "column": "列"}, ...]
    """

def build_gpt_request(
    stores: List[Dict],
    categories: Dict[str, str]
) -> Dict:
    """
    ChatGPT APIリクエストを構築

    Args:
        stores: 店舗リスト
        categories: カテゴリマスタ

    Returns:
        GPT APIリクエストペイロード
    """

def parse_gpt_response(response: str) -> List[Dict]:
    """
    ChatGPT APIレスポンスをパース

    Args:
        response: GPT API レスポンス（JSON文字列）

    Returns:
        パース済み分類結果リスト

    Raises:
        ValueError: JSON解析失敗時
    """

def validate_classification_result(result: Dict) -> bool:
    """
    分類結果の妥当性を検証

    Args:
        result: 分類結果
            {"store": "店舗名", "category": "カテゴリ名", "column": "列"}

    Returns:
        True: 妥当、False: 不正
    """

def apply_default_category(store: str) -> Dict:
    """
    デフォルトカテゴリを適用（フォールバック処理）

    Args:
        store: 店舗名

    Returns:
        デフォルト分類結果（H列: 雑貨費）
    """
```

### ChatGPT API 連携

#### リクエスト形式
```python
request_payload = {
    "model": "gpt-5",
    "messages": [
        {
            "role": "system",
            "content": (
                "あなたは家計簿分類アシスタントです。\n"
                "以下のCSV明細に対して、指定された列カテゴリに分類してください。\n"
                "理由は返さず、JSONのみ返してください。"
            )
        },
        {
            "role": "user",
            "content": json.dumps({
                "mode": "THINK",
                "entries": [
                    {"store": "スターバックス", "amount": 560},
                    {"store": "イオンリテール", "amount": 1234}
                ],
                "categories": {
                    "C": "食材費",
                    "D": "外食費",
                    "E": "自己投資費",
                    "F": "書籍代",
                    "G": "家電",
                    "H": "雑貨費",
                    "I": "衣服・化粧費",
                    "J": "娯楽",
                    "K": "旅行費",
                    "O": "通信費",
                    "R": "個人娯楽",
                    "T": "サブスク"
                },
                "rules": [
                    "出力はJSONのみ",
                    "categoryとcolumnを必ず返す",
                    "分類不能は発生させず、すべて雑貨費（H列）に分類する"
                ]
            }, ensure_ascii=False)
        }
    ],
    "temperature": 0.3,
    "response_format": {"type": "json_object"}
}
```

#### レスポンス形式
```json
[
  {"store": "スターバックス", "category": "外食費", "column": "D"},
  {"store": "イオンリテール", "category": "食材費", "column": "C"}
]
```

### エラーハンドリング

```python
try:
    # ChatGPT API 呼び出し
    result = classify_unregistered_stores(stores, categories)
except OpenAIAPIError as e:
    # API失敗時: デフォルトカテゴリで続行
    logger.error(f"ChatGPT API error: {e}")
    result = [apply_default_category(store["store"]) for store in stores]
except JSONDecodeError as e:
    # JSON解析失敗時: デフォルトカテゴリで続行
    logger.error(f"JSON parse error: {e}")
    result = [apply_default_category(store["store"]) for store in stores]
except Exception as e:
    # その他エラー: デフォルトカテゴリで続行
    logger.error(f"Unexpected error: {e}")
    result = [apply_default_category(store["store"]) for store in stores]
```

### パフォーマンス最適化
- **バッチ処理**: 未登録店舗を一括送信（最大50件/リクエスト）
- **キャッシング**: 同一店舗名の再分類を回避
- **レート制限対応**: exponential backoff でリトライ
- **タイムアウト設定**: 10秒以内に応答がない場合はタイムアウト

### セキュリティ要件
- OpenAI API Key は環境変数`OPENAI_API_KEY`で管理
- `.env`ファイルに保存、`.gitignore`対象
- API Keyのログ出力を禁止

### テストケース
1. **正常系**: 未登録店舗50件を一括分類、全件成功
2. **異常系**: API失敗時、デフォルトカテゴリ（H列）で続行
3. **異常系**: JSON解析失敗時、デフォルトカテゴリで続行
4. **境界値**: 未登録店舗0件、空リスト返却
5. **境界値**: 未登録店舗100件、バッチ分割処理

---

## ダウンロード方法

このファイルをダウンロードするには、以下の手順で操作してください：

1. Artifactの右上にあるダウンロードボタン（↓アイコン）をクリック
2. ファイル名 `backend_modules_spec.md` として保存

または、このテキスト全体をコピーしてテキストエディタに貼り付けて保存してください。