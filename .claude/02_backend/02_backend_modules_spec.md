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

## ダウンロード方法

このファイルをダウンロードするには、以下の手順で操作してください：

1. Artifactの右上にあるダウンロードボタン（↓アイコン）をクリック
2. ファイル名 `backend_modules_spec.md` として保存

または、このテキスト全体をコピーしてテキストエディタに貼り付けて保存してください。