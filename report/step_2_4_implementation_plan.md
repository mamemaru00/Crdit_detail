# Step 2.4: Google Sheets API連携モジュール実装計画書

## 1. 概要

### 1.1 目的
`modules/sheets_api.py`を実装し、Googleスプレッドシートとの認証・接続・読み書き・バッチ更新を行うモジュールを構築します。サービスアカウント認証を使用し、年シート・月行・カテゴリ列への金額加算処理を効率的に実行します。

### 1.2 主な機能
- サービスアカウント認証（`gspread` + `google-auth`）
- スプレッドシート接続・年シート取得
- セル値の読み取り・加算・更新
- バッチ更新によるAPIコール数削減
- APIレート制限対応（リトライ処理）
- 詳細なエラーハンドリングとログ記録

### 1.3 実装スケジュール
- **Phase 1: 基盤実装** (2時間) - 認証、接続、基本機能
- **Phase 2: セル操作** (2時間) - 読み書き、加算ロジック
- **Phase 3: バッチ処理** (2時間) - 一括更新、レート制限対応
- **Phase 4: テスト作成** (3時間) - 単体テスト、統合テスト

**総見積もり**: 9時間

---

## 2. Phase構成

### Phase 1: 基盤実装（認証・接続・基本機能）

#### 実装する関数
1. `authenticate()` - サービスアカウント認証
2. `open_spreadsheet()` - スプレッドシート接続
3. `get_year_sheet()` - 年シート取得
4. `get_month_row()` - 月行番号計算
5. `get_column_index()` - 列名→列番号変換

#### タスクリスト
- [x] カスタム例外クラスの定義（SheetsAPIError系）
- [x] 定数定義（パス、スコープ、レート制限）
- [x] `authenticate()` 実装
  - [x] サービスアカウントJSON読み込み
  - [x] Credentials生成
  - [x] gspreadクライアント認証
  - [x] エラーハンドリング（ファイル不存在、認証失敗）
- [x] `open_spreadsheet()` 実装
  - [x] スプレッドシートIDによる接続
  - [x] エラーハンドリング（スプレッドシート未存在、権限エラー）
- [x] `get_year_sheet()` 実装
  - [x] 年シート名検索（例："2025年"）
  - [x] エラーハンドリング（シート未存在）
- [x] `get_month_row()` 実装
  - [x] 月番号から行番号計算（3 + month）
  - [x] バリデーション（1～12月）
- [x] `get_column_index()` 実装
  - [x] 列名（B～V）→列番号変換
  - [x] バリデーション（B～V以外はエラー）

---

### Phase 2: セル操作（読み書き・加算ロジック）

#### 実装する関数
1. `get_cell_value()` - セル値取得
2. `update_cell_value()` - セル値更新（加算）
3. `_validate_sheet_access()` - シートアクセス検証（内部）

#### タスクリスト
- [x] `get_cell_value()` 実装
  - [x] 指定セルの値取得
  - [x] 空セルは0として扱う
  - [x] エラーハンドリング
- [x] `update_cell_value()` 実装
  - [x] 既存値取得
  - [x] 新規値加算
  - [x] セル更新
  - [x] 更新前後のログ記録
  - [x] エラーハンドリング
- [x] `_validate_sheet_access()` 実装（内部ヘルパー）
  - [x] シートオブジェクトの有効性検証
  - [x] 行・列の範囲検証

---

### Phase 3: バッチ処理（一括更新・レート制限対応）

#### 実装する関数
1. `batch_update_cells()` - バッチ更新
2. `_apply_rate_limit()` - レート制限対応（内部）
3. `_retry_on_api_error()` - APIエラーリトライ（内部）

#### タスクリスト
- [x] `batch_update_cells()` 実装
  - [x] 複数セルの一括更新
  - [x] gspread.Worksheet.batch_update()使用
  - [x] 更新データの検証
  - [x] エラーハンドリング
- [x] `_apply_rate_limit()` 実装（内部ヘルパー）
  - [x] API呼び出し間の待機処理
  - [x] レート制限回避（RATE_LIMIT_WAITを使用）
- [x] `_retry_on_api_error()` 実装（内部ヘルパー）
  - [x] APIエラー時のリトライロジック
  - [x] 指数バックオフ
  - [x] 最大リトライ回数制御

---

### Phase 4: テスト作成（単体テスト・統合テスト）

#### テストスイート構成
- テストファイル: `tests/test_sheets_api.py`
- 単体テスト: 25ケース以上
- 統合テスト: 5ケース以上

#### 単体テストケース（25件以上）
1. **認証テスト（5件）**
   - [x] 正常な認証成功
   - [x] 認証情報ファイル不存在エラー
   - [x] JSON解析エラー
   - [x] 認証情報形式エラー
   - [x] 認証失敗エラー

2. **スプレッドシート接続テスト（4件）**
   - [x] 正常な接続成功
   - [x] スプレッドシートID不正エラー
   - [x] スプレッドシート未存在エラー
   - [x] アクセス権限エラー

3. **年シート取得テスト（4件）**
   - [x] 正常なシート取得
   - [x] シート名形式（"2025年"）検証
   - [x] シート未存在エラー
   - [x] 複数年シート存在時の正しい選択

4. **月行番号計算テスト（4件）**
   - [x] 正常な計算（1月→4行、12月→15行）
   - [x] 月番号範囲外エラー（0月、13月）
   - [x] 境界値テスト（1月、12月）
   - [x] 非整数値エラー

5. **列番号変換テスト（4件）**
   - [x] 正常な変換（B→2, V→22）
   - [x] 列名範囲外エラー（A, W, Z）
   - [x] 境界値テスト（B, V）
   - [x] 小文字入力の処理（b→B）

6. **セル値取得テスト（4件）**
   - [x] 正常な値取得
   - [x] 空セルは0として取得
   - [x] 数値以外のセル値エラー
   - [x] セル範囲外エラー

7. **セル値更新テスト（5件）**
   - [x] 正常な加算更新
   - [x] 空セルへの初回書き込み
   - [x] 更新前後のログ記録検証
   - [x] 更新失敗エラー
   - [x] 負の値の加算処理

8. **バッチ更新テスト（5件）**
   - [x] 正常な一括更新
   - [x] 空リストの処理
   - [x] 最大バッチサイズ超過時の分割処理
   - [x] 部分的な更新失敗エラー
   - [x] 更新データ検証エラー

9. **レート制限対応テスト（3件）**
   - [x] レート制限エラー時の待機処理
   - [x] リトライロジックの動作確認
   - [x] 最大リトライ回数超過時のエラー

10. **エラーハンドリングテスト（2件）**
    - [x] カスタム例外の詳細情報検証
    - [x] 予期しないエラーのハンドリング

#### 統合テスト（5件）
1. [x] エンドツーエンド認証→接続→読み取り
2. [x] エンドツーエンド認証→接続→書き込み
3. [x] バッチ更新による複数セル同時更新
4. [x] レート制限発生時のリトライ動作
5. [x] エラー発生時の適切なロールバック

---

## 3. 実装詳細

### 3.1 カスタム例外クラス

```python
class SheetsAPIError(Exception):
    """Google Sheets API連携の基底例外クラス

    すべてのSheets API関連例外の基底クラスです。
    エラーメッセージと詳細情報を保持します。

    Attributes:
        message (str): エラーメッセージ
        details (Dict): エラーの詳細情報(オプション)
    """

    def __init__(self, message: str, details: Optional[Dict] = None):
        """
        Args:
            message (str): エラーメッセージ
            details (Optional[Dict]): エラーの詳細情報。デフォルトは空の辞書
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(SheetsAPIError):
    """認証エラー

    サービスアカウント認証に失敗した場合に発生します。
    認証情報ファイルの不存在、JSON解析エラー、認証失敗時に使用されます。
    """
    pass


class SpreadsheetNotFoundError(SheetsAPIError):
    """スプレッドシート未検出エラー

    指定されたIDのスプレッドシートが存在しない、または
    アクセス権限がない場合に発生します。
    """
    pass


class SheetNotFoundError(SheetsAPIError):
    """シート未検出エラー

    指定された年のシート（例："2025年"）が存在しない場合に発生します。
    """
    pass


class CellUpdateError(SheetsAPIError):
    """セル更新エラー

    セルの読み取りまたは更新処理が失敗した場合に発生します。
    APIエラー、ネットワークエラー、レート制限超過時に使用されます。
    """
    pass
```

### 3.2 定数定義

```python
# ファイルパス
DEFAULT_CREDENTIALS_PATH = 'config/service_account.json'

# Google Sheets APIスコープ
SPREADSHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# APIレート制限対応
RATE_LIMIT_WAIT = 1.0  # API呼び出し間の待機秒数（秒）
MAX_RETRIES = 3  # 最大リトライ回数
RETRY_BACKOFF_FACTOR = 2.0  # リトライ時のバックオフ係数

# バッチ更新
MAX_BATCH_SIZE = 100  # バッチ更新の最大サイズ

# 月・列の範囲
MIN_MONTH = 1
MAX_MONTH = 12
VALID_COLUMNS = [
    'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
    'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
    'T', 'U', 'V'
]

# スプレッドシート構造
HEADER_ROWS = 3  # ヘッダー行数（タイトル、空行、ヘッダー）
```

### 3.3 関数詳細

#### 3.3.1 authenticate()

**シグネチャ**:
```python
def authenticate(
    credentials_path: str = DEFAULT_CREDENTIALS_PATH
) -> gspread.Client:
    """
    サービスアカウント認証を実行してgspreadクライアントを取得

    Args:
        credentials_path (str): サービスアカウントJSONファイルのパス
            デフォルト: 'config/service_account.json'

    Returns:
        gspread.Client: 認証済みgspreadクライアント

    Raises:
        AuthenticationError: 認証情報ファイルが見つからない、または認証に失敗

    Example:
        >>> client = authenticate()
        >>> client = authenticate('custom/path/service_account.json')
    """
```

**実装ロジック**:
1. 認証情報ファイルの存在確認
2. `Credentials.from_service_account_file()` で認証情報読み込み
3. スコープ設定（`SPREADSHEET_SCOPES`）
4. `gspread.authorize()` でクライアント生成
5. 成功ログ記録
6. エラー時は`AuthenticationError`を投げる

**エラーハンドリング**:
- ファイル不存在: `FileNotFoundError` → `AuthenticationError`
- JSON解析エラー: `json.JSONDecodeError` → `AuthenticationError`
- 認証失敗: `google.auth.exceptions.GoogleAuthError` → `AuthenticationError`

**ログ記録**:
- `INFO`: 認証成功
- `ERROR`: 認証失敗（エラー詳細）

---

#### 3.3.2 open_spreadsheet()

**シグネチャ**:
```python
def open_spreadsheet(
    client: gspread.Client,
    spreadsheet_id: str
) -> gspread.Spreadsheet:
    """
    スプレッドシートに接続

    Args:
        client (gspread.Client): 認証済みクライアント
        spreadsheet_id (str): スプレッドシートID

    Returns:
        gspread.Spreadsheet: スプレッドシートオブジェクト

    Raises:
        SpreadsheetNotFoundError: スプレッドシートが見つからない、または権限エラー

    Example:
        >>> client = authenticate()
        >>> sheet = open_spreadsheet(client, '1A2B3C4D5E...')
    """
```

**実装ロジック**:
1. `client.open_by_key(spreadsheet_id)` でスプレッドシート取得
2. 成功ログ記録（スプレッドシート名、ID）
3. エラー時は`SpreadsheetNotFoundError`を投げる

**エラーハンドリング**:
- スプレッドシート不存在: `gspread.exceptions.SpreadsheetNotFound` → `SpreadsheetNotFoundError`
- アクセス権限エラー: `gspread.exceptions.APIError` → `SpreadsheetNotFoundError`

**ログ記録**:
- `INFO`: 接続成功（スプレッドシート名、ID）
- `ERROR`: 接続失敗（エラー詳細）

---

#### 3.3.3 get_year_sheet()

**シグネチャ**:
```python
def get_year_sheet(
    spreadsheet: gspread.Spreadsheet,
    year: int
) -> gspread.Worksheet:
    """
    年シートを取得（例："2025年"）

    Args:
        spreadsheet (gspread.Spreadsheet): スプレッドシートオブジェクト
        year (int): 対象年（例: 2025）

    Returns:
        gspread.Worksheet: 年シートオブジェクト

    Raises:
        SheetNotFoundError: 指定年のシートが存在しない

    Example:
        >>> worksheet = get_year_sheet(spreadsheet, 2025)
        >>> worksheet.title
        '2025年'
    """
```

**実装ロジック**:
1. シート名を生成（`f"{year}年"`）
2. `spreadsheet.worksheet(sheet_name)` でシート取得
3. 成功ログ記録
4. エラー時は`SheetNotFoundError`を投げる

**エラーハンドリング**:
- シート不存在: `gspread.exceptions.WorksheetNotFound` → `SheetNotFoundError`

**ログ記録**:
- `INFO`: シート取得成功（シート名、年）
- `ERROR`: シート取得失敗（エラー詳細）

---

#### 3.3.4 get_month_row()

**シグネチャ**:
```python
def get_month_row(month: int) -> int:
    """
    月番号から行番号を計算

    計算式: row = 3 + month
    例: 1月 → 4行目、8月 → 11行目、12月 → 15行目

    Args:
        month (int): 月番号（1～12）

    Returns:
        int: 行番号

    Raises:
        ValueError: 月番号が範囲外（1～12以外）

    Example:
        >>> get_month_row(1)
        4
        >>> get_month_row(8)
        11
        >>> get_month_row(12)
        15
    """
```

**実装ロジック**:
1. 月番号の範囲検証（1～12）
2. 行番号計算（`HEADER_ROWS + month`）
3. 結果を返却

**エラーハンドリング**:
- 範囲外: `ValueError`（月番号が1～12以外）

---

#### 3.3.5 get_column_index()

**シグネチャ**:
```python
def get_column_index(column: str) -> int:
    """
    列名（B～V）を列番号に変換

    Args:
        column (str): 列名（B～V）。小文字も受け付ける

    Returns:
        int: 列番号（B=2, C=3, ..., V=22）

    Raises:
        ValueError: 列名が範囲外（B～V以外）

    Example:
        >>> get_column_index('B')
        2
        >>> get_column_index('C')
        3
        >>> get_column_index('V')
        22
        >>> get_column_index('b')  # 小文字も可
        2
    """
```

**実装ロジック**:
1. 列名を大文字に変換
2. 有効列範囲（`VALID_COLUMNS`）に含まれるか検証
3. 列番号計算（`ord(column) - ord('A') + 1`）
4. 結果を返却

**エラーハンドリング**:
- 範囲外: `ValueError`（列名がB～V以外）

---

#### 3.3.6 get_cell_value()

**シグネチャ**:
```python
def get_cell_value(
    worksheet: gspread.Worksheet,
    row: int,
    col: int
) -> int:
    """
    セルの値を取得（空セルは0として扱う）

    Args:
        worksheet (gspread.Worksheet): ワークシートオブジェクト
        row (int): 行番号
        col (int): 列番号

    Returns:
        int: セルの値（整数）。空セルは0

    Raises:
        CellUpdateError: セル取得エラー時

    Example:
        >>> value = get_cell_value(worksheet, 11, 3)
        >>> value
        5780
    """
```

**実装ロジック**:
1. `worksheet.cell(row, col).value` でセル値取得
2. 値が空または`None`の場合は0を返す
3. 数値に変換（`int()`）
4. エラー時は`CellUpdateError`を投げる

**エラーハンドリング**:
- セル範囲外: `gspread.exceptions.APIError` → `CellUpdateError`
- 数値変換エラー: `ValueError` → `CellUpdateError`

---

#### 3.3.7 update_cell_value()

**シグネチャ**:
```python
def update_cell_value(
    worksheet: gspread.Worksheet,
    row: int,
    col: int,
    amount: int
) -> int:
    """
    セルの値を加算更新

    既存値を取得し、amountを加算して更新します。
    更新前後の値をログに記録します（監査用）。

    Args:
        worksheet (gspread.Worksheet): ワークシートオブジェクト
        row (int): 行番号
        col (int): 列番号
        amount (int): 加算する金額

    Returns:
        int: 更新後の値

    Raises:
        CellUpdateError: セル更新エラー時

    Example:
        >>> # 既存値が5780の場合
        >>> new_value = update_cell_value(worksheet, 11, 3, 1200)
        >>> new_value
        6980
    """
```

**実装ロジック**:
1. `get_cell_value()` で既存値取得
2. 新規値計算（`current_value + amount`）
3. `worksheet.update_cell(row, col, new_value)` で更新
4. 更新前後の値をログ記録（監査用）
5. 新規値を返却

**エラーハンドリング**:
- 更新失敗: `gspread.exceptions.APIError` → `CellUpdateError`

**ログ記録**:
- `INFO`: 更新成功（セル位置、更新前後の値）
- `ERROR`: 更新失敗（エラー詳細）

---

#### 3.3.8 batch_update_cells()

**シグネチャ**:
```python
def batch_update_cells(
    worksheet: gspread.Worksheet,
    updates: List[Dict[str, int]]
) -> int:
    """
    複数セルを一括更新（バッチ処理）

    APIコール数を削減するため、複数セルを一度に更新します。
    更新件数がMAX_BATCH_SIZEを超える場合は自動的に分割します。

    Args:
        worksheet (gspread.Worksheet): ワークシートオブジェクト
        updates (List[Dict[str, int]]): 更新データリスト
            [
                {'row': 4, 'col': 2, 'amount': 1000},
                {'row': 5, 'col': 3, 'amount': 2000},
                ...
            ]

    Returns:
        int: 更新されたセル数

    Raises:
        CellUpdateError: バッチ更新エラー時

    Example:
        >>> updates = [
        ...     {'row': 4, 'col': 2, 'amount': 1000},
        ...     {'row': 5, 'col': 3, 'amount': 2000}
        ... ]
        >>> count = batch_update_cells(worksheet, updates)
        >>> count
        2
    """
```

**実装ロジック**:
1. 更新データの検証（必須フィールド確認）
2. 更新件数がMAX_BATCH_SIZEを超える場合は分割
3. 各セルの既存値取得
4. 新規値計算（既存値 + amount）
5. `worksheet.batch_update()` で一括更新
6. レート制限対応（`_apply_rate_limit()`）
7. 更新件数を返却

**エラーハンドリング**:
- 更新データ検証エラー: `ValueError` → `CellUpdateError`
- バッチ更新失敗: `gspread.exceptions.APIError` → `CellUpdateError`

**ログ記録**:
- `INFO`: バッチ更新成功（更新件数）
- `DEBUG`: 各セルの更新詳細
- `ERROR`: 更新失敗（エラー詳細）

---

#### 3.3.9 _apply_rate_limit() （内部ヘルパー）

**シグネチャ**:
```python
def _apply_rate_limit() -> None:
    """
    APIレート制限回避のための待機処理（内部ヘルパー関数）

    RATE_LIMIT_WAIT秒間待機してAPIコールのレートを制限します。
    """
```

**実装ロジック**:
1. `time.sleep(RATE_LIMIT_WAIT)` で待機
2. デバッグログ記録

---

#### 3.3.10 _retry_on_api_error() （内部ヘルパー）

**シグネチャ**:
```python
def _retry_on_api_error(
    func: Callable,
    *args,
    **kwargs
) -> Any:
    """
    APIエラー時のリトライロジック（内部ヘルパー関数）

    指数バックオフを使用してAPIエラー時にリトライします。
    最大MAX_RETRIES回までリトライし、それでも失敗した場合は例外を投げます。

    Args:
        func (Callable): リトライ対象の関数
        *args: 関数の引数
        **kwargs: 関数のキーワード引数

    Returns:
        Any: 関数の戻り値

    Raises:
        CellUpdateError: 最大リトライ回数超過時
    """
```

**実装ロジック**:
1. `MAX_RETRIES` 回までリトライ
2. APIエラー時は指数バックオフ（`RETRY_BACKOFF_FACTOR ** retry_count`）で待機
3. 成功したら結果を返却
4. 最大リトライ回数超過時は`CellUpdateError`を投げる

---

#### 3.3.11 _validate_sheet_access() （内部ヘルパー）

**シグネチャ**:
```python
def _validate_sheet_access(
    worksheet: gspread.Worksheet,
    row: int,
    col: int
) -> None:
    """
    シートアクセスの有効性を検証（内部ヘルパー関数）

    Args:
        worksheet (gspread.Worksheet): ワークシートオブジェクト
        row (int): 行番号
        col (int): 列番号

    Raises:
        ValueError: シートオブジェクトが無効、または行・列が範囲外
    """
```

**実装ロジック**:
1. ワークシートオブジェクトの有効性確認
2. 行番号の範囲確認（1以上）
3. 列番号の範囲確認（1以上）
4. エラー時は`ValueError`を投げる

---

## 4. セキュリティ要件

### 4.1 認証情報管理
- **認証情報ファイル**: `config/service_account.json`
- **Git管理**: `.gitignore`に追加済み（機密情報を含まない）
- **エラーログ**: 認証情報を含めない（パスのみ記録）

### 4.2 エラーハンドリング
- **機密情報の露出防止**: エラーログに認証情報を含めない
- **詳細情報**: `details`パラメータで構造化された情報を提供
- **ユーザーフレンドリー**: 日本語エラーメッセージ

### 4.3 API使用制限
- **レート制限**: `RATE_LIMIT_WAIT`を使用してAPIコールを制限
- **リトライロジック**: 指数バックオフでAPIエラーを回避
- **バッチ処理**: `MAX_BATCH_SIZE`を超える場合は分割処理

---

## 5. テスト計画

### 5.1 単体テスト戦略
- **mockライブラリ**: `unittest.mock`を使用
- **外部依存**: gspread、google-authをmock化
- **ファイルI/O**: 一時ファイルを使用してテスト

### 5.2 統合テスト戦略
- **テストスプレッドシート**: 専用のテスト用スプレッドシートを使用
- **認証情報**: テスト用サービスアカウントを使用
- **クリーンアップ**: テスト後にデータを元に戻す

### 5.3 カバレッジ目標
- **関数カバレッジ**: 100%（全11関数）
- **分岐カバレッジ**: 90%以上
- **テストケース**: 30件以上（単体25件、統合5件）

---

## 6. 実装スケジュール詳細

### Phase 1: 基盤実装（2時間）
- **時間配分**:
  - カスタム例外・定数定義: 30分
  - `authenticate()`: 30分
  - `open_spreadsheet()`, `get_year_sheet()`: 30分
  - `get_month_row()`, `get_column_index()`: 30分

### Phase 2: セル操作（2時間）
- **時間配分**:
  - `get_cell_value()`: 30分
  - `update_cell_value()`: 60分
  - `_validate_sheet_access()`: 30分

### Phase 3: バッチ処理（2時間）
- **時間配分**:
  - `batch_update_cells()`: 60分
  - `_apply_rate_limit()`, `_retry_on_api_error()`: 60分

### Phase 4: テスト作成（3時間）
- **時間配分**:
  - 単体テスト作成（25件）: 120分
  - 統合テスト作成（5件）: 60分

---

## 7. コーディング規約

### 7.1 スタイルガイド
- **PEP 8準拠**: 行の長さ、インデント、命名規則
- **型ヒント**: 全パラメータ・戻り値に型ヒント
- **docstring**: Google形式（既存コードに準拠）

### 7.2 ログ記録方針
- **ログレベル**:
  - `DEBUG`: 詳細な処理内容（セル更新の詳細など）
  - `INFO`: 重要な操作（認証成功、更新成功など）
  - `WARNING`: 警告（リトライ発生など）
  - `ERROR`: エラー（認証失敗、更新失敗など）
- **監査ログ**: セル更新時は更新前後の値を記録

### 7.3 エラーメッセージ
- **日本語**: ユーザー向けメッセージは日本語
- **詳細情報**: `details`パラメータで構造化
- **例**:
  ```python
  raise AuthenticationError(
      "認証情報ファイルが見つかりません",
      details={'path': credentials_path}
  )
  ```

---

## 8. 依存ライブラリ

### 8.1 必須ライブラリ
```python
import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import GoogleAuthError
import time
import json
from pathlib import Path
from typing import List, Optional, Dict, Callable, Any
import logging
```

### 8.2 バージョン要件
- `gspread>=6.0.0`
- `google-auth>=2.23.0`
- `google-api-python-client>=2.100.0`

---

## 9. 完成イメージ

### 9.1 使用例
```python
import logging
from modules.sheets_api import (
    authenticate,
    open_spreadsheet,
    get_year_sheet,
    get_month_row,
    get_column_index,
    update_cell_value,
    batch_update_cells
)

# ロガー設定
logging.basicConfig(level=logging.INFO)

# 認証
client = authenticate()

# スプレッドシート接続
spreadsheet = open_spreadsheet(client, '1A2B3C4D5E...')

# 年シート取得
worksheet = get_year_sheet(spreadsheet, 2025)

# セル更新（8月の外食費に5780円を加算）
row = get_month_row(8)  # 11行目
col = get_column_index('C')  # 3列目
new_value = update_cell_value(worksheet, row, col, 5780)

# バッチ更新
updates = [
    {'row': 4, 'col': 2, 'amount': 1000},
    {'row': 5, 'col': 3, 'amount': 2000}
]
batch_update_cells(worksheet, updates)
```

### 9.2 ログ出力例
```
INFO:modules.sheets_api:認証に成功しました
INFO:modules.sheets_api:スプレッドシートに接続しました: '家計簿2025' (ID: 1A2B3C4D5E...)
INFO:modules.sheets_api:年シートを取得しました: '2025年'
INFO:modules.sheets_api:[CELL:UPDATE] セル更新成功 - 位置=(11, 3), 更新前=5780, 更新後=11560, 加算=5780
INFO:modules.sheets_api:[BATCH:UPDATE] バッチ更新成功 - 更新件数=2件
```

---

## 10. 承認基準

### 10.1 Phase完了条件
- **Phase 1**: 認証・接続・基本機能が正常に動作
- **Phase 2**: セル読み書き・加算ロジックが正常に動作
- **Phase 3**: バッチ更新・レート制限対応が正常に動作
- **Phase 4**: 単体テスト25件以上、統合テスト5件以上が合格

### 10.2 最終承認基準
- [ ] 全11関数が実装完了
- [ ] PEP 8準拠100%
- [ ] 型ヒント完全性100%
- [ ] docstring完全性100%
- [ ] 単体テスト25件以上合格
- [ ] 統合テスト5件以上合格
- [ ] 関数カバレッジ100%
- [ ] 分岐カバレッジ90%以上
- [ ] セキュリティ要件充足
- [ ] ログ記録完全性100%

---

## 11. リスクと対策

### 11.1 リスク項目
1. **APIレート制限超過**
   - 対策: `RATE_LIMIT_WAIT`でAPIコールを制限、リトライロジック実装

2. **認証失敗**
   - 対策: 詳細なエラーメッセージ、認証情報ファイルの存在確認

3. **ネットワークエラー**
   - 対策: リトライロジック、タイムアウト設定

4. **テスト環境の不足**
   - 対策: mockライブラリでgspreadをmock化

### 11.2 パフォーマンス目標
- **1000件データ処理**: 30秒以内（バッチ更新使用）
- **APIコール数**: 最小化（バッチ処理活用）

---

## 12. まとめ

本計画書に基づき、`modules/sheets_api.py`を実装することで、Google Sheets APIとの堅牢な連携モジュールが完成します。既存コード（`mapping_manager.py`, `category_logic.py`）と同様の高品質なコードを目指し、PEP 8準拠、型ヒント、docstring、詳細なエラーハンドリング、監査ログを実装します。

**総見積もり**: 9時間
**実装関数数**: 11関数（8パブリック、3プライベート）
**テストケース**: 30件以上
**コード品質**: A+（プロダクション品質）
