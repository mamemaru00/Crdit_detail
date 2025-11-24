# Step 2.1: CSV処理モジュール作成 作業計画（修正版）

## 修正履歴
- **初版作成日**: 2025-11-16
- **修正日**: 2025-11-16
- **修正理由**: project-orchestrator の指摘事項（5つの承認条件）を反映

## 主要な修正点
1. **【承認条件1】** 事前確認項目に「実際のCSVサンプル提供依頼」を追加
2. **【承認条件2】** データ構造を完全化（user, payment_method, note フィールドを追加）
3. **【承認条件3】** ファイルパスバリデーション関数 `validate_file_path()` を追加（パストラバーサル対策）
4. **【承認条件4】** モジュール名を `csv_processor.py` → `csv_parser.py` に統一
5. **【承認条件5】** 金額のカンマ除去処理を追加
6. **【中優先度改善】** CP932フォールバック処理を追加
7. **【中優先度改善】** テストデータに特殊文字（髙、﨑、①、②）を追加
8. **【低優先度改善】** ログ出力ガイドライン（個人情報マスキング）を明示
9. **【低優先度改善】** カバレッジ目標（80%以上）を設定

---

## 1. 事前確認項目

### 1.1 ドキュメント確認
- [ ] `.claude/02_backend/05_csv_record_definition.md` を読んで、CSVレコード定義を確認
- [ ] `.claude/02_backend/02_backend_modules_spec.md` を読んで、モジュール仕様（csv_parser.py）を確認
- [ ] `.claude/02_backend/01_backend_api_routes.md` を読んで、API連携方法を理解
- [ ] `.claude/06_security/security_requirements.md` を読んで、ファイルアップロードとエンコーディング処理のセキュリティ要件を確認
- [ ] `.claude/09_test/00_backend_test_specification.md` を読んで、テスト要件を確認

### 1.2 環境確認
- [ ] `modules/` ディレクトリが存在することを確認
- [ ] `requirements.txt` に `pandas` と `chardet` が含まれていることを確認
- [ ] Python 仮想環境がアクティブであることを確認（venv）
- [ ] 依存パッケージがインストール済みであることを確認

### 1.3 ディレクトリ構造確認
- [ ] プロジェクトルートの構造が設計通りであることを確認
- [ ] `modules/` ディレクトリ内に他のモジュールファイルのプレースホルダーがあるか確認

### **【修正】1.4 CSVサンプル確認（承認条件1）**
- [ ] **【重要】ユーザーに実際のイオンカード明細CSVサンプル（個人情報削除済み）の提供を依頼**
- [ ] CSV構造を確認（列番号、ヘッダー行数、金額フォーマット、特殊文字の有無）
- [ ] 以下の項目を具体的に確認:
  - ヘッダー行数（想定: 7行）
  - 明細開始行（想定: 8行目）
  - 列0: 利用日（YYMMDD形式）
  - 列1: 利用者区分（例: "本人"）
  - 列2: 利用先（店舗名）
  - 列3: 支払方法（例: "１回"）
  - 列6: 利用金額（カンマ区切りの有無を確認）
  - 列7または8: 備考（Apple Pay利用分など）
  - 特殊文字の使用例（髙、﨑、①、②など）

### 1.5 テスト用データ準備計画
- [ ] CSVサンプルが入手できた場合: 実データをベースにテストデータを作成
- [ ] CSVサンプルが入手できない場合: `.claude/02_backend/05_csv_record_definition.md` を参照してサンプルを作成
- [ ] テスト用CSVにShift_JISエンコーディングを適用

---

## 2. モジュール設計

### **【修正】2.1 ファイル構成（承認条件4: モジュール名を統一）**

```python
# modules/csv_parser.py（旧: csv_processor.py）

"""
イオンカード明細CSV処理モジュール

このモジュールはイオンカード利用明細CSVファイルを処理し、
必要なデータを抽出・変換する機能を提供します。

主な機能:
- CSVファイルの読み込み（Shift_JIS → UTF-8変換、CP932フォールバック対応）
- 明細データの抽出（9行目以降、6桁数字で始まる行。8行目はカラムヘッダー）
- 全フィールドの抽出（date, user, store, payment_method, amount, note）
- 日付変換（YYMMDD → YYYY/MM/DD）
- プレビューデータの生成
- ファイルパス検証（パストラバーサル対策）
"""

# インポート
import pandas as pd
import chardet
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import os

# 定数定義
ENCODING_DETECTION_BYTES = 10000  # エンコーディング検出に使用するバイト数
PREVIEW_ROWS = 5  # プレビュー表示行数
DETAIL_START_ROW = 8  # 明細データ開始行（0インデックス）
DATE_PATTERN = r'^\d{6}$'  # 6桁数字パターン（YYMMDD）
MAX_FILE_SIZE = 10 * 1024 * 1024  # 最大ファイルサイズ 10MB

# カスタム例外クラス
class CSVProcessingError(Exception):
    """CSV処理の基底例外クラス"""
    pass

class EncodingDetectionError(CSVProcessingError):
    """エンコーディング検出エラー"""
    pass

class InvalidFileFormatError(CSVProcessingError):
    """無効なファイル形式エラー"""
    pass

class DateConversionError(CSVProcessingError):
    """日付変換エラー"""
    pass

class DataExtractionError(CSVProcessingError):
    """データ抽出エラー"""
    pass

class PathValidationError(CSVProcessingError):
    """ファイルパス検証エラー"""
    pass

# 関数定義（詳細は後述）
```

### **【修正】2.2 関数一覧と役割（承認条件3: validate_file_path を追加）**

| 関数名 | 役割 | 入力 | 出力 | 例外 |
|--------|------|------|------|------|
| **【新規】** `validate_file_path(file_path, allowed_dir)` | ファイルパスが許可されたディレクトリ内にあることを確認 | ファイルパス、許可ディレクトリ | bool | `PathValidationError` |
| `detect_encoding(file_path)` | ファイルのエンコーディングを検出（CP932フォールバック対応） | ファイルパス | エンコーディング名（str） | `EncodingDetectionError` |
| `read_csv_file(file_path)` | CSVファイルを読み込みDataFrameに変換 | ファイルパス | pandas.DataFrame | `InvalidFileFormatError`, `EncodingDetectionError` |
| **【修正】** `extract_detail_data(df)` | 明細データ（9行目以降）を抽出（全フィールド） | DataFrame | DataFrame（date, user, store, payment_method, amount, note） | `DataExtractionError` |
| `is_detail_row(row)` | 行が明細行か判定（6桁数字で始まる） | Series | bool | なし |
| `convert_date_format(yymmdd_str)` | YYMMDD → YYYY/MM/DD 変換 | 文字列（6桁） | 文字列（YYYY/MM/DD） | `DateConversionError` |
| `extract_month_number(yymmdd_str)` | 月番号を抽出（1-12） | 文字列（6桁） | int | `DateConversionError` |
| **【修正】** `process_csv_file(file_path)` | CSVファイル全体を処理（統合関数、完全データ構造対応） | ファイルパス | Dict（全フィールド含む明細データリスト） | 各種例外 |
| `generate_preview(detail_data)` | プレビューデータを生成（先頭5件） | 明細データリスト | List[Dict] | なし |
| `validate_file_size(file_path)` | ファイルサイズを検証 | ファイルパス | bool | `InvalidFileFormatError` |

**合計**: 10関数（前回の9関数から1関数追加）

### **【修正】2.3 データフロー（承認条件2: 全フィールド対応）**

```
1. ファイルアップロード
   ↓
2. validate_file_path() - パストラバーサル検証（新規）
   ↓
3. validate_file_size() - ファイルサイズチェック（10MB以下）
   ↓
4. detect_encoding() - エンコーディング検出（chardet使用、CP932フォールバック）
   ↓
5. read_csv_file() - CSVファイル読み込み（Shift_JIS/CP932 → UTF-8）
   ↓
6. extract_detail_data() - 明細データ抽出（修正版）
   ├─ is_detail_row() で各行を判定（6桁数字で始まるか）
   ├─ 列0（date）、列1（user）、列2（store）、列3（payment_method）、列6（amount）、列7/8（note）を抽出
   ├─ 金額列のカンマ除去処理（新規）
   └─ convert_date_format() で日付変換（YYMMDD → YYYY/MM/DD）
   ↓
7. generate_preview() - プレビューデータ生成（先頭5件）
   ↓
8. 結果返却（JSON形式、全フィールド含む）
```

---

## 3. 実装計画

### 3.1 ファイル読込関数

#### **【新規】3.1.1 `validate_file_path(file_path: str, allowed_dir: str) -> bool`（承認条件3）**

**目的**: パストラバーサル攻撃を防止し、ファイルが許可されたディレクトリ内にあることを確認

**実装詳細**:
```python
def validate_file_path(file_path: str, allowed_dir: str) -> bool:
    """
    ファイルパスが許可されたディレクトリ内にあることを確認する

    パストラバーサル攻撃（../../../etc/passwdなど）を防止するための検証。

    Args:
        file_path: 検証するファイルパス
        allowed_dir: 許可されたディレクトリのパス

    Returns:
        True（ファイルが許可されたディレクトリ内にある場合）

    Raises:
        PathValidationError: ファイルパスが不正な場合

    Example:
        >>> validate_file_path('/tmp/uploads/file.csv', '/tmp/uploads')
        True
        >>> validate_file_path('/tmp/uploads/../../../etc/passwd', '/tmp/uploads')
        PathValidationError
    """
    # 実装ポイント:
    # 1. pathlib.Path を使用してパスを正規化
    # 2. resolve() で絶対パスに変換（シンボリックリンク解決）
    # 3. 正規化後のパスが allowed_dir 配下にあるか確認
    # 4. allowed_dir 外の場合は PathValidationError を発生
    # 5. ファイルが存在しない場合も検証（FileNotFoundError）

    try:
        # パスを正規化
        normalized_file_path = Path(file_path).resolve()
        normalized_allowed_dir = Path(allowed_dir).resolve()

        # allowed_dir 配下にあるか確認
        if not normalized_file_path.is_relative_to(normalized_allowed_dir):
            raise PathValidationError(
                f"ファイルパスが許可されたディレクトリ外です: {file_path}"
            )

        return True
    except ValueError as e:
        raise PathValidationError(f"ファイルパスの検証に失敗しました: {e}")
```

**セキュリティ考慮事項**:
- パストラバーサル攻撃の防止（`../` を使った上位ディレクトリへのアクセス拒否）
- シンボリックリンクの解決（実際のファイルパスを取得）
- 許可されたディレクトリ外へのアクセス拒否

**テストケース**:
- 正常系: 許可ディレクトリ内のファイルパス
- 異常系: `../../../etc/passwd` のようなパストラバーサル
- 異常系: シンボリックリンクを使った許可ディレクトリ外へのアクセス
- 異常系: 存在しないファイルパス

#### **【修正】3.1.2 `detect_encoding(file_path: str) -> str`（CP932フォールバック追加）**

**目的**: ファイルのエンコーディングを自動検出（CP932フォールバック対応）

**実装詳細**:
```python
def detect_encoding(file_path: str) -> str:
    """
    ファイルのエンコーディングを検出する（CP932フォールバック対応）

    chardetでShift_JISまたはCP932を検出。
    検出失敗時はCP932でのフォールバック試行を実施。

    Args:
        file_path: CSVファイルのパス

    Returns:
        検出されたエンコーディング名（例: 'shift_jis', 'cp932', 'utf-8'）

    Raises:
        EncodingDetectionError: エンコーディング検出に失敗した場合
        FileNotFoundError: ファイルが存在しない場合
    """
    # 実装ポイント:
    # 1. ファイルの先頭10000バイトを読み込む
    # 2. chardet.detect() でエンコーディングを検出
    # 3. 検出結果の信頼度（confidence）が0.7未満の場合:
    #    a. CP932での読み込みを試行
    #    b. 成功したら 'cp932' を返す
    #    c. 失敗したら例外を発生
    # 4. Shift_JIS検出時はCP932も考慮（エイリアス処理）
    # 5. エンコーディング名を小文字で返す
    # 6. エラーハンドリング（ファイルが開けない、検出失敗）

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(ENCODING_DETECTION_BYTES)

        # chardetで検出
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']

        # 信頼度が低い場合はCP932フォールバック
        if confidence < 0.7:
            try:
                raw_data.decode('cp932')
                return 'cp932'
            except UnicodeDecodeError:
                raise EncodingDetectionError(
                    f"エンコーディング検出の信頼度が低く、CP932でも読み込めませんでした。"
                    f"検出結果: {encoding} (信頼度: {confidence})"
                )

        # Shift_JISの場合はCP932も試す（Windows環境対応）
        if encoding.lower() in ['shift_jis', 'shift-jis']:
            try:
                raw_data.decode('cp932')
                return 'cp932'
            except UnicodeDecodeError:
                return 'shift_jis'

        return encoding.lower()

    except FileNotFoundError:
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
    except Exception as e:
        raise EncodingDetectionError(f"エンコーディング検出中にエラーが発生しました: {e}")
```

**セキュリティ考慮事項**:
- ファイルパスのバリデーション（パストラバーサル攻撃防止）は `validate_file_path()` で事前実施
- ファイルサイズチェック（メモリ枯渇防止）は `validate_file_size()` で事前実施
- 読み込みバイト数の制限（ENCODING_DETECTION_BYTES）

**テストケース**:
- 正常系: Shift_JIS エンコードされたCSVファイル
- 正常系: CP932 エンコードされたCSVファイル（特殊文字含む）
- 正常系: UTF-8 エンコードされたCSVファイル
- 異常系: 存在しないファイルパス
- 異常系: バイナリファイル（画像など）
- 異常系: 空ファイル
- 異常系: 信頼度が低いファイル（CP932フォールバックテスト）

#### 3.1.3 `validate_file_size(file_path: str) -> bool`

**目的**: ファイルサイズが上限以下であることを確認

**実装詳細**:
```python
def validate_file_size(file_path: str) -> bool:
    """
    ファイルサイズを検証する

    Args:
        file_path: CSVファイルのパス

    Returns:
        True（サイズが許容範囲内の場合）

    Raises:
        InvalidFileFormatError: ファイルサイズが上限を超える場合
    """
    # 実装ポイント:
    # 1. pathlib.Path().stat().st_size でファイルサイズを取得
    # 2. MAX_FILE_SIZE（10MB）と比較
    # 3. 超過している場合は例外を発生（エラーメッセージに具体的なサイズを含める）

    file_size = Path(file_path).stat().st_size
    max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
    current_size_mb = file_size / (1024 * 1024)

    if file_size > MAX_FILE_SIZE:
        raise InvalidFileFormatError(
            f"ファイルサイズが上限（{max_size_mb}MB）を超えています。"
            f"ファイルサイズ: {current_size_mb:.2f}MB"
        )

    return True
```

**セキュリティ考慮事項**:
- DoS攻撃防止（大容量ファイルのアップロード拒否）
- メモリ使用量の制限

#### **【修正】3.1.4 `read_csv_file(file_path: str) -> pd.DataFrame`（CP932対応）**

**目的**: CSVファイルを読み込み、DataFrameに変換

**実装詳細**:
```python
def read_csv_file(file_path: str) -> pd.DataFrame:
    """
    CSVファイルを読み込み、DataFrameに変換する

    Args:
        file_path: CSVファイルのパス

    Returns:
        pandas.DataFrame（全行・全列）

    Raises:
        InvalidFileFormatError: CSV形式が不正な場合
        EncodingDetectionError: エンコーディング検出に失敗した場合
    """
    # 実装ポイント:
    # 1. detect_encoding() でエンコーディングを検出（CP932対応）
    # 2. pandas.read_csv() で読み込み
    #    - encoding: 検出されたエンコーディング
    #    - header: None（ヘッダー行なし）
    #    - dtype: str（全列を文字列として読み込み）
    # 3. エラーハンドリング（UnicodeDecodeError, ParserError など）
    # 4. DataFrameが空でないことを確認

    encoding = detect_encoding(file_path)

    try:
        df = pd.read_csv(
            file_path,
            encoding=encoding,
            header=None,
            dtype=str
        )

        if df.empty:
            raise InvalidFileFormatError("CSVファイルが空です。")

        return df

    except UnicodeDecodeError as e:
        raise InvalidFileFormatError(
            f"ファイルの読み込みに失敗しました（エンコーディングエラー）: {e}"
        )
    except pd.errors.ParserError as e:
        raise InvalidFileFormatError(
            f"CSVファイルの形式が不正です: {e}"
        )
```

**セキュリティ考慮事項**:
- エンコーディングエラーの安全な処理（errors='replace' は使用しない）
- CSV インジェクション対策（数式として解釈されないようにする）

**テストケース**:
- 正常系: 正しい形式のイオンカード明細CSV（Shift_JIS）
- 正常系: CP932エンコードのCSV（特殊文字含む）
- 異常系: 不正なCSV形式（カンマ欠損、列数不一致）
- 異常系: 空ファイル
- 異常系: テキストファイルだがCSVではない

### 3.2 明細データ抽出関数

#### 3.2.1 `is_detail_row(row: pd.Series) -> bool`

**目的**: 行が明細行かどうかを判定

**実装詳細**:
```python
def is_detail_row(row: pd.Series) -> bool:
    """
    行が明細データ行かどうかを判定する

    明細行の条件:
    - 列0が6桁の数字で始まる（YYMMDD形式）

    Args:
        row: DataFrameの1行（pandas.Series）

    Returns:
        True（明細行の場合）、False（それ以外）
    """
    # 実装ポイント:
    # 1. row[0]（列0）が存在するか確認
    # 2. 文字列型に変換
    # 3. 正規表現 r'^\d{6}' でマッチするか判定
    # 4. None や NaN の場合は False を返す

    if pd.isna(row[0]):
        return False

    date_str = str(row[0]).strip()
    return bool(re.match(DATE_PATTERN, date_str))
```

**テストケース**:
- 正常系: "250115" で始まる行（True）
- 正常系: "240312" で始まる行（True）
- 異常系: "25/01/15" で始まる行（False）
- 異常系: "利用日" で始まる行（False）
- 異常系: 空文字列（False）
- 異常系: None（False）

#### **【修正】3.2.2 `extract_detail_data(df: pd.DataFrame) -> pd.DataFrame`（承認条件2, 5）**

**目的**: 9行目以降の明細データを抽出し、必要な全列を取得（user, payment_method, note を追加、金額カンマ除去対応）
※ 8行目（インデックス7）はカラムヘッダー行

**実装詳細**:
```python
def extract_detail_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    明細データを抽出する（全フィールド対応）

    処理内容:
    1. 9行目以降の行を対象とする（インデックス8以降）
       ※ 8行目（インデックス7）はカラムヘッダーのため、is_detail_row()でフィルタリングされる
    2. 列0が6桁数字で始まる行のみを抽出
    3. 【修正】列0（date）、列1（user）、列2（store）、列3（payment_method）、列6（amount）、列7/8（note）を取得
    4. 【修正】金額列のカンマを除去（例: "5,780" → "5780"）
    5. 日付を YYYY/MM/DD 形式に変換
    6. 【修正】列名を 'date', 'user', 'store', 'payment_method', 'amount', 'note' に変更

    Args:
        df: CSVから読み込んだDataFrame

    Returns:
        抽出・変換後のDataFrame（全フィールド含む）

    Raises:
        DataExtractionError: データ抽出に失敗した場合
    """
    # 実装ポイント:
    # 1. df.iloc[DETAIL_START_ROW:] で9行目以降を取得（DETAIL_START_ROW=8）
    # 2. apply() と is_detail_row() で明細行をフィルタリング
    # 3. 必要な列が存在することを確認（列0, 1, 2, 3, 6, 7または8）
    # 4. 必要な列のみを抽出
    # 5. 【新規】金額列（列6）のカンマを除去
    # 6. 列0に対して convert_date_format() を適用
    # 7. 【新規】備考欄（列7または8）を取得（存在しない場合は空文字列）
    # 8. 列名を変更（rename）
    # 9. 金額列のバリデーション（数値に変換可能か確認）
    # 10. 空のDataFrameの場合は例外

    try:
        # 9行目以降を取得（DETAIL_START_ROW=8、インデックス8以降）
        details_df = df.iloc[DETAIL_START_ROW:].copy()

        # 明細行のみをフィルタリング
        mask = details_df.apply(is_detail_row, axis=1)
        details_df = details_df[mask]

        if details_df.empty:
            raise DataExtractionError(
                "明細データが見つかりませんでした。"
                "CSVファイルに9行目以降の明細データが含まれていることを確認してください。"
            )

        # 必要な列の存在確認
        required_cols = [0, 1, 2, 3, 6]
        for col in required_cols:
            if col not in details_df.columns:
                raise DataExtractionError(
                    f"必要な列（列{col}）が存在しません。CSVファイルの形式を確認してください。"
                )

        # 備考欄の列番号を判定（列7または列8）
        note_col = 7 if 7 in details_df.columns else (8 if 8 in details_df.columns else None)

        # 必要な列のみを抽出
        if note_col is not None:
            extracted_df = details_df[[0, 1, 2, 3, 6, note_col]].copy()
            column_names = ['date', 'user', 'store', 'payment_method', 'amount', 'note']
        else:
            extracted_df = details_df[[0, 1, 2, 3, 6]].copy()
            extracted_df['note'] = ''  # 備考欄が存在しない場合は空文字列
            column_names = ['date', 'user', 'store', 'payment_method', 'amount', 'note']

        # 列名を変更
        extracted_df.columns = column_names

        # 【新規】金額列のカンマを除去
        extracted_df['amount'] = extracted_df['amount'].astype(str).str.replace(',', '')

        # 金額列のバリデーション（数値に変換可能か確認）
        try:
            extracted_df['amount'] = pd.to_numeric(extracted_df['amount'], errors='coerce')
            if extracted_df['amount'].isna().any():
                invalid_rows = extracted_df[extracted_df['amount'].isna()]
                raise DataExtractionError(
                    f"金額列に数値でない値が含まれています。無効な行数: {len(invalid_rows)}"
                )
        except ValueError as e:
            raise DataExtractionError(f"金額列の変換に失敗しました: {e}")

        # 日付を YYYY/MM/DD 形式に変換
        extracted_df['date'] = extracted_df['date'].apply(convert_date_format)

        return extracted_df

    except DataExtractionError:
        raise
    except Exception as e:
        raise DataExtractionError(f"データ抽出中にエラーが発生しました: {e}")
```

**セキュリティ考慮事項**:
- 列番号の存在確認（IndexError 防止）
- データ欠損の安全な処理
- 金額列の数値バリデーション（SQLインジェクション対策）
- カンマ除去による不正な値の検出

**テストケース**:
- 正常系: 明細行が10件あるCSV（全フィールド含む）
- 正常系: 金額にカンマが含まれるCSV（例: "5,780"）
- 正常系: 備考欄が列7にあるCSV
- 正常系: 備考欄が列8にあるCSV
- 正常系: 備考欄が存在しないCSV
- 正常系: 明細行が1件のみのCSV
- 異常系: 明細行が0件のCSV
- 異常系: 列6（金額）が存在しないCSV
- 異常系: 列6が数値でない行を含むCSV
- 異常系: 7行以下のCSV（8行目が存在しない）

### 3.3 日付変換関数

#### 3.3.1 `convert_date_format(yymmdd_str: str) -> str`

**目的**: YYMMDD 形式を YYYY/MM/DD 形式に変換

**実装詳細**:
```python
def convert_date_format(yymmdd_str: str) -> str:
    """
    YYMMDD形式の日付をYYYY/MM/DD形式に変換する

    変換ルール:
    - YY が 00-49 の場合 → 2000年代（2000-2049）
    - YY が 50-99 の場合 → 1900年代（1950-1999）

    例:
    - "250115" → "2025/01/15"
    - "240312" → "2024/03/12"
    - "991231" → "1999/12/31"

    Args:
        yymmdd_str: 6桁の日付文字列（YYMMDD）

    Returns:
        変換後の日付文字列（YYYY/MM/DD）

    Raises:
        DateConversionError: 日付形式が不正な場合
    """
    # 実装ポイント:
    # 1. 入力が6桁の数字文字列であることを検証
    # 2. YY, MM, DD に分割（スライス）
    # 3. YY を int に変換し、2000年代/1900年代を判定
    # 4. MM が 01-12 の範囲内であることを検証
    # 5. DD が 01-31 の範囲内であることを検証（簡易チェック）
    # 6. "YYYY/MM/DD" 形式の文字列を構築
    # 7. エラーハンドリング（不正な値の場合は例外）

    # 6桁の数字文字列であることを検証
    if not re.match(DATE_PATTERN, yymmdd_str):
        raise DateConversionError(
            f"日付形式が不正です: {yymmdd_str}。YYMMDD形式の6桁数字である必要があります。"
        )

    # YY, MM, DD に分割
    yy = int(yymmdd_str[0:2])
    mm = int(yymmdd_str[2:4])
    dd = int(yymmdd_str[4:6])

    # 年の判定（00-49 → 2000年代、50-99 → 1900年代）
    if yy <= 49:
        yyyy = 2000 + yy
    else:
        yyyy = 1900 + yy

    # 月のバリデーション
    if not (1 <= mm <= 12):
        raise DateConversionError(
            f"月が不正です: {mm}。1-12の範囲である必要があります。"
        )

    # 日のバリデーション（簡易チェック）
    if not (1 <= dd <= 31):
        raise DateConversionError(
            f"日が不正です: {dd}。1-31の範囲である必要があります。"
        )

    return f"{yyyy}/{mm:02d}/{dd:02d}"
```

**セキュリティ考慮事項**:
- 入力値の厳密なバリデーション（正規表現による検証）
- 範囲外の値の拒否（MM: 13, DD: 32 など）

**テストケース**:
- 正常系: "250115" → "2025/01/15"
- 正常系: "240229" → "2024/02/29"（閏年）
- 正常系: "000101" → "2000/01/01"（境界値）
- 正常系: "491231" → "2049/12/31"（境界値）
- 正常系: "500101" → "1950/01/01"（境界値）
- 正常系: "991231" → "1999/12/31"（境界値）
- 異常系: "25011" → DateConversionError（5桁）
- 異常系: "2501155" → DateConversionError（7桁）
- 異常系: "251301" → DateConversionError（月が13）
- 異常系: "250132" → DateConversionError（日が32）
- 異常系: "25AB01" → DateConversionError（非数字）

#### 3.3.2 `extract_month_number(yymmdd_str: str) -> int`

**目的**: YYMMDD 形式から月番号（1-12）を抽出

**実装詳細**:
```python
def extract_month_number(yymmdd_str: str) -> int:
    """
    YYMMDD形式の日付から月番号を抽出する

    Args:
        yymmdd_str: 6桁の日付文字列（YYMMDD）

    Returns:
        月番号（1-12のint）

    Raises:
        DateConversionError: 日付形式が不正な場合
    """
    # 実装ポイント:
    # 1. 入力が6桁の数字文字列であることを検証
    # 2. 3-4文字目（インデックス2:4）を抽出
    # 3. int に変換
    # 4. 1-12 の範囲内であることを検証
    # 5. エラーハンドリング

    if not re.match(DATE_PATTERN, yymmdd_str):
        raise DateConversionError(
            f"日付形式が不正です: {yymmdd_str}。YYMMDD形式の6桁数字である必要があります。"
        )

    mm = int(yymmdd_str[2:4])

    if not (1 <= mm <= 12):
        raise DateConversionError(
            f"月が不正です: {mm}。1-12の範囲である必要があります。"
        )

    return mm
```

**テストケース**:
- 正常系: "250115" → 1
- 正常系: "241231" → 12
- 異常系: "250015" → DateConversionError（月が0）
- 異常系: "251301" → DateConversionError（月が13）

### 3.4 プレビュー生成関数

#### 3.4.1 `generate_preview(detail_data: List[Dict]) -> List[Dict]`

**目的**: 明細データの先頭5件をプレビューとして返す

**実装詳細**:
```python
def generate_preview(detail_data: List[Dict]) -> List[Dict]:
    """
    プレビューデータを生成する（先頭5件）

    Args:
        detail_data: 明細データのリスト
            各要素は {'date': str, 'user': str, 'store': str,
                      'payment_method': str, 'amount': int, 'note': str} の辞書

    Returns:
        先頭5件のデータリスト（5件未満の場合は全件）
    """
    # 実装ポイント:
    # 1. detail_data[:PREVIEW_ROWS] でスライス
    # 2. 空リストの場合は空リストを返す
    # 3. 各要素が正しい形式（全フィールド）であることを確認

    return detail_data[:PREVIEW_ROWS]
```

**テストケース**:
- 正常系: 10件のデータ → 先頭5件を返す
- 正常系: 3件のデータ → 3件すべてを返す
- 正常系: 空リスト → 空リストを返す

### 3.5 エラーハンドリング

#### 3.5.1 カスタム例外クラスの定義

**実装詳細**:
```python
class CSVProcessingError(Exception):
    """CSV処理の基底例外クラス"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class EncodingDetectionError(CSVProcessingError):
    """エンコーディング検出エラー"""
    pass

class InvalidFileFormatError(CSVProcessingError):
    """無効なファイル形式エラー"""
    pass

class DateConversionError(CSVProcessingError):
    """日付変換エラー"""
    pass

class DataExtractionError(CSVProcessingError):
    """データ抽出エラー"""
    pass

class PathValidationError(CSVProcessingError):
    """ファイルパス検証エラー"""
    pass
```

#### **【修正】3.5.2 エラーメッセージの設計（個人情報マスキング明示）**

**日本語エラーメッセージ**（ユーザー向け）:
- ファイルパスエラー: "ファイルパスが許可されたディレクトリ外です。"
- ファイルサイズエラー: "ファイルサイズが上限（10MB）を超えています。ファイルサイズ: {size}MB"
- エンコーディングエラー: "ファイルのエンコーディングを検出できませんでした。Shift_JIS形式のCSVファイルをアップロードしてください。"
- 形式エラー: "CSVファイルの形式が不正です。イオンカード利用明細CSVファイルをアップロードしてください。"
- データ欠損エラー: "必要なデータが見つかりませんでした。CSVファイルに明細データ（8行目以降）が含まれていることを確認してください。"
- 日付エラー: "日付形式が不正です: {value}。YYMMDD形式の6桁数字である必要があります。"

**【新規】ログメッセージ**（開発者向け、個人情報マスキング方針）:
- 詳細なスタックトレース
- 処理中のファイルパス
- エラー発生時の行番号・列番号
- **【重要】個人情報マスキング方針**:
  - 店舗名: ログに記録OK（カテゴリ判定に必要）
  - 金額: ログに記録OK（集計処理の検証に必要）
  - 利用者区分（"本人"など）: ログに記録OK（匿名化されている）
  - 支払方法: ログに記録OK（匿名化されている）
  - 利用日: ログに記録OK（個人特定に直結しない）
  - **備考欄**: ログに記録しない（個人情報が含まれる可能性がある）
  - **ファイルパス**: 相対パスのみ記録（絶対パスは記録しない）

**ログ出力例**:
```python
# OK
logger.info(f"明細データ抽出: 店舗名={store_name}, 金額={amount}, 日付={date}")

# NG（備考欄を含む）
logger.info(f"明細データ: {row}")  # row に note が含まれる場合はNG

# OK（備考欄をマスキング）
logger.info(f"明細データ: 日付={date}, 店舗={store}, 金額={amount}, 備考=[マスク]")
```

#### **【修正】3.5.3 統合処理関数（承認条件2: 全フィールド対応）**

**実装詳細**:
```python
def process_csv_file(file_path: str, allowed_dir: str = '/tmp/uploads') -> Dict:
    """
    CSVファイルを処理し、明細データとプレビューを返す（全フィールド対応）

    Args:
        file_path: CSVファイルのパス
        allowed_dir: 許可されたディレクトリ（デフォルト: /tmp/uploads）

    Returns:
        {
            'details': List[Dict],  # 全明細データ（全フィールド含む）
            'preview': List[Dict],  # プレビューデータ（先頭5件）
            'total_count': int,     # 総件数
            'summary': {            # サマリー情報
                'total_amount': int,
                'date_range': {
                    'start': str,
                    'end': str
                }
            }
        }

        # 各明細データの構造（承認条件2に準拠）:
        {
            'date': str,             # YYYY/MM/DD形式
            'year': int,             # 年（例: 2025）
            'month': int,            # 月番号（1-12）
            'month_str': str,        # 月表示（例: "2025年8月"）
            'store': str,            # 店舗名
            'amount': int,           # 金額
            'user': str,             # 利用者区分（例: "本人"）
            'payment_method': str,   # 支払方法（例: "１回"）
            'note': str              # 備考（空文字列の場合あり）
        }

    Raises:
        各種 CSVProcessingError サブクラス
    """
    # 実装ポイント:
    # 1. validate_file_path() でファイルパスチェック（パストラバーサル対策）
    # 2. validate_file_size() でファイルサイズチェック
    # 3. read_csv_file() でCSV読み込み
    # 4. extract_detail_data() で明細データ抽出（全フィールド）
    # 5. DataFrameをリスト形式に変換
    # 6. 【新規】year, month, month_str フィールドを追加
    # 7. generate_preview() でプレビュー生成
    # 8. サマリー情報の計算（総件数、合計金額、日付範囲）
    # 9. 結果を辞書形式で返却
    # 10. すべての例外を適切にキャッチしてログ出力（個人情報マスキング）

    try:
        # 1. ファイルパス検証
        validate_file_path(file_path, allowed_dir)

        # 2. ファイルサイズ検証
        validate_file_size(file_path)

        # 3. CSV読み込み
        df = read_csv_file(file_path)

        # 4. 明細データ抽出（全フィールド）
        detail_df = extract_detail_data(df)

        # 5. DataFrameをリスト形式に変換
        details = detail_df.to_dict('records')

        # 6. year, month, month_str フィールドを追加
        for record in details:
            # 日付から年と月を抽出（YYYY/MM/DD形式）
            date_parts = record['date'].split('/')
            year = int(date_parts[0])
            month = int(date_parts[1])

            record['year'] = year
            record['month'] = month
            record['month_str'] = f"{year}年{month}月"

        # 7. プレビュー生成
        preview = generate_preview(details)

        # 8. サマリー情報の計算
        total_count = len(details)
        total_amount = sum(record['amount'] for record in details)

        # 日付範囲の計算
        dates = [record['date'] for record in details]
        date_range = {
            'start': min(dates) if dates else '',
            'end': max(dates) if dates else ''
        }

        # 9. 結果を辞書形式で返却
        return {
            'details': details,
            'preview': preview,
            'total_count': total_count,
            'summary': {
                'total_amount': total_amount,
                'date_range': date_range
            }
        }

    except CSVProcessingError:
        # カスタム例外はそのまま再発生
        raise
    except Exception as e:
        # 予期しない例外はログ出力して再発生
        # 【重要】個人情報はログに含めない
        logger.error(f"CSV処理中に予期しないエラーが発生しました: {e}", exc_info=True)
        raise CSVProcessingError(f"CSV処理中にエラーが発生しました: {e}")
```

**データ構造例**（承認条件2に完全準拠）:
```python
{
    'details': [
        {
            'date': '2025/08/15',
            'year': 2025,
            'month': 8,
            'month_str': '2025年8月',
            'store': 'ユシンヤカマタテン',
            'amount': 5780,
            'user': '本人',
            'payment_method': '１回',
            'note': ''
        },
        # ... 他の明細データ
    ],
    'preview': [
        # 先頭5件のデータ（上記と同じ構造）
    ],
    'total_count': 17,
    'summary': {
        'total_amount': 27575,
        'date_range': {
            'start': '2025/08/01',
            'end': '2025/08/31'
        }
    }
}
```

---

## 4. テスト計画

### **【修正】4.1 テストデータ準備（特殊文字追加）**

#### 4.1.1 正常系テストデータ

**ファイル名**: `test_data/sample_valid.csv`

**内容**:
```csv
（1-7行目: ヘッダー情報）
250115,本人,イオン新潟南店,１回,,,5280,,
250116,本人,ファミリーマート,１回,,,1200,,
250117,本人,JR東日本,１回,,,2840,,
250118,本人,マクドナルド,１回,,,890,,
250119,本人,Amazon.co.jp,１回,,,1980,,
250120,本人,イオン新潟南店,１回,,,3560,,Apple Pay利用分
```

**特徴**:
- Shift_JIS エンコーディング
- 8行目以降に明細データ
- 列0: 6桁日付（YYMMDD）
- 列1: 利用者区分（"本人"）
- 列2: 店舗名
- 列3: 支払方法（"１回"）
- 列6: 金額
- 列8: 備考（最終行のみ）

#### **【新規】4.1.2 特殊文字テストデータ（中優先度改善）**

**ファイル名**: `test_data/sample_special_chars.csv`

**内容**:
```csv
（1-7行目: ヘッダー情報）
250115,本人,髙島屋,１回,,,5280,,
250116,本人,﨑陽軒,１回,,,1200,,
250117,本人,①番街,１回,,,2840,,
250118,本人,カフェ②,１回,,,890,,
250119,本人,Amazon①,１回,,,1980,,
```

**特徴**:
- CP932エンコーディング
- 特殊文字（髙、﨑、①、②）を含む店舗名
- エンコーディング検出・変換の正確性を検証

#### **【修正】4.1.3 金額カンマ区切りテストデータ（承認条件5）**

**ファイル名**: `test_data/sample_amount_comma.csv`

**内容**:
```csv
（1-7行目: ヘッダー情報）
250115,本人,イオン新潟南店,１回,,,"5,280",,
250116,本人,ファミリーマート,１回,,,"1,200",,
250117,本人,JR東日本,１回,,,"12,840",,
250118,本人,マクドナルド,１回,,,890,,
250119,本人,Amazon.co.jp,１回,,,"21,980",,
```

**特徴**:
- 金額にカンマ区切りを含む（"5,280"形式）
- カンマ除去処理の検証

#### 4.1.4 異常系テストデータ

**ケース1: エンコーディング異常**
- ファイル名: `test_data/sample_utf8.csv`
- 内容: UTF-8エンコーディング（検出テスト用）

**ケース2: 空ファイル**
- ファイル名: `test_data/sample_empty.csv`
- 内容: 0バイト

**ケース3: 明細データなし**
- ファイル名: `test_data/sample_no_details.csv`
- 内容: ヘッダーのみ（7行）

**ケース4: 不正な日付**
- ファイル名: `test_data/sample_invalid_date.csv`
- 内容: 列0に "25/01/15" などの形式（6桁数字でない）

**ケース5: 列数不足**
- ファイル名: `test_data/sample_missing_columns.csv`
- 内容: 列6が存在しない

**ケース6: 大容量ファイル**
- ファイル名: `test_data/sample_large.csv`
- 内容: 11MB（上限超過テスト用）

**【新規】ケース7: パストラバーサル攻撃**
- ファイル名: `../../../etc/passwd`
- 内容: パストラバーサル攻撃のシミュレーション

### 4.2 単体テスト仕様

#### **【新規】4.2.1 `test_validate_file_path.py`（承認条件3）**

```python
import pytest
from modules.csv_parser import validate_file_path, PathValidationError

class TestValidateFilePath:
    """ファイルパス検証関数のテスト"""

    def test_valid_path_in_allowed_dir(self):
        """許可ディレクトリ内のパスで正常終了すること"""
        # Given: 許可ディレクトリ内のファイルパス
        # When: validate_file_path()を呼び出す
        # Then: True が返されること

    def test_path_traversal_attack(self):
        """パストラバーサル攻撃で例外が発生すること"""
        # Given: "../../../etc/passwd" のようなパス
        # When: validate_file_path()を呼び出す
        # Then: PathValidationError が発生すること

    def test_symlink_outside_allowed_dir(self):
        """シンボリックリンクを使った許可ディレクトリ外へのアクセスで例外が発生すること"""
        # Given: 許可ディレクトリ外を指すシンボリックリンク
        # When: validate_file_path()を呼び出す
        # Then: PathValidationError が発生すること

    def test_nonexistent_path(self):
        """存在しないパスで例外が発生すること"""
        # Given: 存在しないファイルパス
        # When: validate_file_path()を呼び出す
        # Then: FileNotFoundError が発生すること
```

#### **【修正】4.2.2 `test_detect_encoding.py`（CP932対応）**

```python
import pytest
from modules.csv_parser import detect_encoding, EncodingDetectionError

class TestDetectEncoding:
    """エンコーディング検出関数のテスト"""

    def test_detect_shift_jis(self):
        """Shift_JISファイルを正しく検出できること"""
        # Given: Shift_JISエンコードされたCSVファイル
        # When: detect_encoding()を呼び出す
        # Then: 'shift_jis' または 'cp932' が返されること

    def test_detect_cp932(self):
        """CP932ファイル（特殊文字含む）を正しく検出できること"""
        # Given: CP932エンコードされたCSVファイル（髙、﨑を含む）
        # When: detect_encoding()を呼び出す
        # Then: 'cp932' が返されること

    def test_detect_utf8(self):
        """UTF-8ファイルを正しく検出できること"""
        # Given: UTF-8エンコードされたCSVファイル
        # When: detect_encoding()を呼び出す
        # Then: 'utf-8' が返されること

    def test_file_not_found(self):
        """存在しないファイルパスで例外が発生すること"""
        # Given: 存在しないファイルパス
        # When: detect_encoding()を呼び出す
        # Then: FileNotFoundError が発生すること

    def test_binary_file(self):
        """バイナリファイルで例外が発生すること"""
        # Given: 画像ファイル（PNG）
        # When: detect_encoding()を呼び出す
        # Then: EncodingDetectionError が発生すること

    def test_empty_file(self):
        """空ファイルで例外が発生すること"""
        # Given: 0バイトのファイル
        # When: detect_encoding()を呼び出す
        # Then: EncodingDetectionError が発生すること

    def test_low_confidence_fallback(self):
        """信頼度が低い場合にCP932フォールバックが機能すること"""
        # Given: chardetの信頼度が0.7未満のファイル
        # When: detect_encoding()を呼び出す
        # Then: CP932での読み込みが試行され、成功すれば 'cp932' が返されること
```

#### 4.2.3 `test_validate_file_size.py`

```python
import pytest
from modules.csv_parser import validate_file_size, InvalidFileFormatError

class TestValidateFileSize:
    """ファイルサイズ検証関数のテスト"""

    def test_valid_size(self):
        """10MB以下のファイルで正常終了すること"""
        # Given: 5MBのCSVファイル
        # When: validate_file_size()を呼び出す
        # Then: True が返されること

    def test_max_size(self):
        """ちょうど10MBのファイルで正常終了すること"""
        # Given: 10MBのCSVファイル
        # When: validate_file_size()を呼び出す
        # Then: True が返されること

    def test_oversized_file(self):
        """10MBを超えるファイルで例外が発生すること"""
        # Given: 11MBのCSVファイル
        # When: validate_file_size()を呼び出す
        # Then: InvalidFileFormatError が発生すること
        # And: エラーメッセージにファイルサイズが含まれること
```

#### 4.2.4 `test_read_csv_file.py`

```python
import pytest
import pandas as pd
from modules.csv_parser import read_csv_file, InvalidFileFormatError

class TestReadCsvFile:
    """CSV読み込み関数のテスト"""

    def test_read_valid_csv(self):
        """正常なCSVファイルを読み込めること"""
        # Given: 正常なShift_JIS CSVファイル
        # When: read_csv_file()を呼び出す
        # Then: DataFrameが返されること
        # And: 全列が文字列型であること

    def test_read_utf8_csv(self):
        """UTF-8のCSVファイルも読み込めること"""
        # Given: UTF-8エンコードされたCSVファイル
        # When: read_csv_file()を呼び出す
        # Then: DataFrameが返されること

    def test_read_cp932_csv(self):
        """CP932のCSVファイル（特殊文字含む）を読み込めること"""
        # Given: CP932エンコードされたCSVファイル（髙、﨑を含む）
        # When: read_csv_file()を呼び出す
        # Then: DataFrameが返されること
        # And: 特殊文字が正しく読み込まれていること

    def test_invalid_csv_format(self):
        """不正なCSV形式で例外が発生すること"""
        # Given: カンマが欠損したCSVファイル
        # When: read_csv_file()を呼び出す
        # Then: InvalidFileFormatError が発生すること

    def test_empty_csv(self):
        """空のCSVファイルで例外が発生すること"""
        # Given: 空のCSVファイル
        # When: read_csv_file()を呼び出す
        # Then: InvalidFileFormatError が発生すること
```

#### 4.2.5 `test_is_detail_row.py`

```python
import pytest
import pandas as pd
from modules.csv_parser import is_detail_row

class TestIsDetailRow:
    """明細行判定関数のテスト"""

    def test_valid_detail_row(self):
        """6桁数字で始まる行がTrueを返すこと"""
        # Given: 列0が "250115" の行
        # When: is_detail_row()を呼び出す
        # Then: True が返されること

    def test_header_row(self):
        """ヘッダー行がFalseを返すこと"""
        # Given: 列0が "利用日" の行
        # When: is_detail_row()を呼び出す
        # Then: False が返されること

    def test_formatted_date_row(self):
        """スラッシュ区切りの日付行がFalseを返すこと"""
        # Given: 列0が "25/01/15" の行
        # When: is_detail_row()を呼び出す
        # Then: False が返されること

    def test_empty_row(self):
        """空の行がFalseを返すこと"""
        # Given: 列0が空文字列の行
        # When: is_detail_row()を呼び出す
        # Then: False が返されること

    def test_none_row(self):
        """Noneを含む行がFalseを返すこと"""
        # Given: 列0が None の行
        # When: is_detail_row()を呼び出す
        # Then: False が返されること
```

#### **【修正】4.2.6 `test_extract_detail_data.py`（全フィールド対応、カンマ除去テスト追加）**

```python
import pytest
import pandas as pd
from modules.csv_parser import extract_detail_data, DataExtractionError

class TestExtractDetailData:
    """明細データ抽出関数のテスト"""

    def test_extract_valid_details(self):
        """正常なデータから明細を抽出できること（全フィールド）"""
        # Given: 正常なDataFrame（10行の明細を含む）
        # When: extract_detail_data()を呼び出す
        # Then: 10行のDataFrameが返されること
        # And: 列名が 'date', 'user', 'store', 'payment_method', 'amount', 'note' であること
        # And: 日付が YYYY/MM/DD 形式に変換されていること

    def test_extract_with_comma_amount(self):
        """金額にカンマが含まれるデータを正しく処理できること"""
        # Given: 金額列に "5,280" のようなカンマ区切りを含むDataFrame
        # When: extract_detail_data()を呼び出す
        # Then: カンマが除去され、数値として処理されること
        # And: amount列が int型であること

    def test_extract_with_note_col7(self):
        """備考欄が列7にあるデータを抽出できること"""
        # Given: 備考欄が列7にあるDataFrame
        # When: extract_detail_data()を呼び出す
        # Then: note列に備考データが含まれること

    def test_extract_with_note_col8(self):
        """備考欄が列8にあるデータを抽出できること"""
        # Given: 備考欄が列8にあるDataFrame
        # When: extract_detail_data()を呼び出す
        # Then: note列に備考データが含まれること

    def test_extract_without_note(self):
        """備考欄が存在しないデータを抽出できること"""
        # Given: 備考欄が存在しないDataFrame
        # When: extract_detail_data()を呼び出す
        # Then: note列が空文字列であること

    def test_extract_single_detail(self):
        """1件のみの明細を抽出できること"""
        # Given: 1行のみ明細を含むDataFrame
        # When: extract_detail_data()を呼び出す
        # Then: 1行のDataFrameが返されること

    def test_no_details(self):
        """明細が0件の場合に例外が発生すること"""
        # Given: 明細行が存在しないDataFrame
        # When: extract_detail_data()を呼び出す
        # Then: DataExtractionError が発生すること

    def test_missing_column(self):
        """必要な列が存在しない場合に例外が発生すること"""
        # Given: 列6が存在しないDataFrame
        # When: extract_detail_data()を呼び出す
        # Then: DataExtractionError が発生すること

    def test_invalid_amount(self):
        """金額が数値でない場合に例外が発生すること"""
        # Given: 列6に "abc" が含まれる行
        # When: extract_detail_data()を呼び出す
        # Then: DataExtractionError が発生すること
```

#### 4.2.7 `test_convert_date_format.py`

```python
import pytest
from modules.csv_parser import convert_date_format, DateConversionError

class TestConvertDateFormat:
    """日付変換関数のテスト"""

    def test_convert_2025(self):
        """2025年の日付を正しく変換できること"""
        # Given: "250115"
        # When: convert_date_format()を呼び出す
        # Then: "2025/01/15" が返されること

    def test_convert_2000(self):
        """2000年の日付を正しく変換できること"""
        # Given: "000101"
        # When: convert_date_format()を呼び出す
        # Then: "2000/01/01" が返されること

    def test_convert_2049_boundary(self):
        """2049年（境界値）を正しく変換できること"""
        # Given: "491231"
        # When: convert_date_format()を呼び出す
        # Then: "2049/12/31" が返されること

    def test_convert_1950_boundary(self):
        """1950年（境界値）を正しく変換できること"""
        # Given: "500101"
        # When: convert_date_format()を呼び出す
        # Then: "1950/01/01" が返されること

    def test_convert_1999(self):
        """1999年の日付を正しく変換できること"""
        # Given: "991231"
        # When: convert_date_format()を呼び出す
        # Then: "1999/12/31" が返されること

    def test_invalid_length(self):
        """6桁でない場合に例外が発生すること"""
        # Given: "25011" (5桁)
        # When: convert_date_format()を呼び出す
        # Then: DateConversionError が発生すること

    def test_invalid_month(self):
        """月が13の場合に例外が発生すること"""
        # Given: "251301"
        # When: convert_date_format()を呼び出す
        # Then: DateConversionError が発生すること

    def test_invalid_day(self):
        """日が32の場合に例外が発生すること"""
        # Given: "250132"
        # When: convert_date_format()を呼び出す
        # Then: DateConversionError が発生すること

    def test_non_numeric(self):
        """数字でない場合に例外が発生すること"""
        # Given: "25AB01"
        # When: convert_date_format()を呼び出す
        # Then: DateConversionError が発生すること
```

#### 4.2.8 `test_extract_month_number.py`

```python
import pytest
from modules.csv_parser import extract_month_number, DateConversionError

class TestExtractMonthNumber:
    """月番号抽出関数のテスト"""

    def test_extract_january(self):
        """1月を正しく抽出できること"""
        # Given: "250115"
        # When: extract_month_number()を呼び出す
        # Then: 1 が返されること

    def test_extract_december(self):
        """12月を正しく抽出できること"""
        # Given: "241231"
        # When: extract_month_number()を呼び出す
        # Then: 12 が返されること

    def test_invalid_month_zero(self):
        """月が0の場合に例外が発生すること"""
        # Given: "250015"
        # When: extract_month_number()を呼び出す
        # Then: DateConversionError が発生すること

    def test_invalid_month_13(self):
        """月が13の場合に例外が発生すること"""
        # Given: "251301"
        # When: extract_month_number()を呼び出す
        # Then: DateConversionError が発生すること
```

#### 4.2.9 `test_generate_preview.py`

```python
import pytest
from modules.csv_parser import generate_preview

class TestGeneratePreview:
    """プレビュー生成関数のテスト"""

    def test_generate_preview_full(self):
        """10件のデータから5件のプレビューを生成できること"""
        # Given: 10件の明細データ（全フィールド含む）
        # When: generate_preview()を呼び出す
        # Then: 5件のリストが返されること

    def test_generate_preview_partial(self):
        """3件のデータから3件のプレビューを生成できること"""
        # Given: 3件の明細データ
        # When: generate_preview()を呼び出す
        # Then: 3件のリストが返されること

    def test_generate_preview_empty(self):
        """空のデータから空のプレビューを生成できること"""
        # Given: 空のリスト
        # When: generate_preview()を呼び出す
        # Then: 空のリストが返されること
```

#### **【修正】4.2.10 `test_process_csv_file.py`（全フィールド対応）**

```python
import pytest
from modules.csv_parser import process_csv_file

class TestProcessCsvFile:
    """CSV処理統合関数のテスト"""

    def test_process_valid_csv(self):
        """正常なCSVファイルを処理できること（全フィールド対応）"""
        # Given: 正常なCSVファイル（10件の明細）
        # When: process_csv_file()を呼び出す
        # Then: 以下の構造の辞書が返されること
        #   - details: 10件のリスト（全フィールド含む）
        #   - preview: 5件のリスト
        #   - total_count: 10
        #   - summary: {total_amount, date_range}
        # And: 各明細に year, month, month_str フィールドが含まれること

    def test_process_large_csv(self):
        """1000件のCSVファイルを30秒以内に処理できること"""
        # Given: 1000件の明細を含むCSVファイル
        # When: process_csv_file()を呼び出す（処理時間を計測）
        # Then: 30秒以内に完了すること
        # And: 正しい結果が返されること

    def test_process_oversized_csv(self):
        """10MBを超えるファイルで例外が発生すること"""
        # Given: 11MBのCSVファイル
        # When: process_csv_file()を呼び出す
        # Then: InvalidFileFormatError が発生すること

    def test_process_path_traversal(self):
        """パストラバーサル攻撃で例外が発生すること"""
        # Given: "../../../etc/passwd" のようなパス
        # When: process_csv_file()を呼び出す
        # Then: PathValidationError が発生すること
```

### **【修正】4.3 統合テスト仕様（カバレッジ目標追加）**

#### 4.3.1 エンドツーエンドテスト

```python
class TestCSVProcessingIntegration:
    """CSV処理のエンドツーエンド統合テスト"""

    def test_full_workflow(self):
        """ファイルアップロードから処理完了までの全体フローが正常に動作すること"""
        # 1. 実際のイオンカード明細CSVファイルを準備
        # 2. process_csv_file()で処理
        # 3. 結果の検証:
        #    - 全明細が正しく抽出されていること
        #    - 日付が YYYY/MM/DD 形式に変換されていること
        #    - 月番号が正しいこと
        #    - year, month, month_str フィールドが正しいこと
        #    - プレビューが5件であること
        #    - 合計金額が正しいこと
```

#### **【新規】4.3.2 カバレッジ目標（低優先度改善）**

**目標**: コードカバレッジ 80%以上

**計測方法**:
```bash
# カバレッジ計測
pytest --cov=modules.csv_parser --cov-report=html

# カバレッジレポート確認
open htmlcov/index.html
```

**カバレッジ基準**:
- **関数カバレッジ**: 100%（全関数がテストされていること）
- **行カバレッジ**: 80%以上（主要な処理パスがテストされていること）
- **分岐カバレッジ**: 80%以上（if/else の両方がテストされていること）

**未カバレッジ許容範囲**:
- 予期しない例外のキャッチブロック（通常は発生しない）
- ログ出力のみの行
- デバッグ用のコード

### 4.4 パフォーマンステスト仕様

```python
class TestPerformance:
    """パフォーマンステスト"""

    def test_1000_records_within_30_seconds(self):
        """1000件のデータを30秒以内に処理できること"""
        # Given: 1000件の明細を含むCSVファイル
        # When: process_csv_file()を実行（時間計測）
        # Then: 30秒以内に完了すること

    def test_10mb_file_processing(self):
        """10MBのファイルを処理できること"""
        # Given: ちょうど10MBのCSVファイル
        # When: process_csv_file()を実行
        # Then: 正常に処理が完了すること
```

---

## **【修正】5. Git 操作計画（6段階コミットを維持）**

### 5.1 ブランチ戦略

**現在のブランチ**: `main`（Phase 1 完了済み）

**新規ブランチ作成**:
```bash
# main から feature/backend-csv-parser を作成
git checkout main
git pull origin main  # 最新を取得
git checkout -b feature/backend-csv-parser
```

### 5.2 コミット計画

#### **【修正】コミット1: カスタム例外クラスとユーティリティ関数（validate_file_path 追加）**

**ファイル**:
- `modules/csv_parser.py` (新規作成)
  - カスタム例外クラス定義（PathValidationError 追加）
  - 定数定義
  - `validate_file_path()` **【新規】**
  - `detect_encoding()` **【修正: CP932フォールバック対応】**
  - `validate_file_size()`

**コミットメッセージ案**:
```
Add CSV parser base structure and file utilities

CSV処理モジュールの基本構造とファイルユーティリティを追加:
- カスタム例外クラス（CSVProcessingError系、PathValidationError追加）の定義
- ファイルパス検証関数（validate_file_path）の実装（パストラバーサル対策）
- エンコーディング検出関数（detect_encoding）の実装（CP932フォールバック対応）
- ファイルサイズ検証関数（validate_file_size）の実装
- chardet によるShift_JIS/CP932自動検出機能

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### **【修正】コミット2: CSV読み込みと明細抽出関数（全フィールド対応、カンマ除去）**

**ファイル**:
- `modules/csv_parser.py` (追記)
  - `read_csv_file()` **【修正: CP932対応】**
  - `is_detail_row()`
  - `extract_detail_data()` **【修正: user, payment_method, note 追加、カンマ除去】**

**コミットメッセージ案**:
```
Add CSV reading and detail extraction functions

CSV読み込みと明細データ抽出機能を追加（全フィールド対応）:
- read_csv_file: Shift_JIS/CP932 CSVをDataFrameに変換
- is_detail_row: 明細行判定（6桁数字パターンマッチング）
- extract_detail_data: 8行目以降の明細データ抽出
  - 全フィールド対応（date, user, store, payment_method, amount, note）
  - 金額のカンマ除去処理を実装
  - 備考欄（列7または8）の柔軟な検出

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### コミット3: 日付変換関数

**ファイル**:
- `modules/csv_parser.py` (追記)
  - `convert_date_format()`
  - `extract_month_number()`

**コミットメッセージ案**:
```
Add date conversion functions

日付変換機能を追加:
- convert_date_format: YYMMDD → YYYY/MM/DD 変換
- extract_month_number: 月番号抽出（1-12）
- 年の判定ロジック（2000年代/1950年代判定）実装

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### **【修正】コミット4: プレビュー生成と統合処理関数（全フィールド対応）**

**ファイル**:
- `modules/csv_parser.py` (追記)
  - `generate_preview()`
  - `process_csv_file()` **【修正: year, month, month_str フィールド追加】**

**コミットメッセージ案**:
```
Add preview generation and integrated processing

プレビュー生成と統合処理機能を追加（完全データ構造対応）:
- generate_preview: 先頭5件のプレビューデータ生成
- process_csv_file: CSV処理の統合関数（全フィールド対応）
  - year, month, month_str フィールドの自動生成
  - サマリー情報（総件数、合計金額、日付範囲）の集計
  - 個人情報マスキングを考慮したログ出力

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### **【修正】コミット5: 単体テストコード（全機能対応）**

**ファイル**:
- `tests/test_csv_parser.py` (新規作成)
  - 全関数の単体テスト（validate_file_path 含む）
  - 特殊文字テスト
  - カンマ除去テスト
  - CP932フォールバックテスト

**コミットメッセージ案**:
```
Add unit tests for CSV parser module

CSV処理モジュールの単体テストを追加（カバレッジ80%以上）:
- ファイルパス検証テスト（パストラバーサル対策検証）
- エンコーディング検出テスト（CP932フォールバック検証）
- ファイルサイズ検証テスト
- CSV読み込みテスト（特殊文字対応検証）
- 明細抽出テスト（全フィールド、カンマ除去検証）
- 日付変換テスト（境界値テスト含む）
- 異常系テスト（エラーハンドリング検証）

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### **【修正】コミット6: テストデータとドキュメント更新（特殊文字データ追加）**

**ファイル**:
- `tests/test_data/` (新規作成)
  - `sample_valid.csv`
  - `sample_special_chars.csv` **【新規】**
  - `sample_amount_comma.csv` **【新規】**
  - `sample_invalid_*.csv`
- `.claude/00_project/08_dev_step.md` (更新)
  - Step 2.1 のチェックボックスを完了に変更

**コミットメッセージ案**:
```
Add test data and update development steps

テストデータと開発ステップドキュメントを更新:
- 正常系・異常系テストデータの追加
- 特殊文字テストデータ（髙、﨑、①、②）の追加
- 金額カンマ区切りテストデータの追加
- Step 2.1（CSV処理モジュール）の完了マーク

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 5.3 プッシュ計画

```bash
# リモートにプッシュ
git push -u origin feature/backend-csv-parser

# プッシュ確認
git status
```

### 5.4 プルリクエスト作成（オプション）

**PR タイトル**:
```
[Step 2.1] CSV処理モジュール実装（csv_parser.py）
```

**PR 説明文**:
```markdown
## 概要
Step 2.1: CSV処理モジュール（modules/csv_parser.py）を実装しました。

## 実装内容
- [x] ファイル読込機能（Shift_JIS/CP932自動検出・UTF-8変換）
- [x] ファイルパス検証（パストラバーサル対策）
- [x] 明細データ抽出（8行目以降、6桁数字判定、全フィールド対応）
- [x] 金額のカンマ除去処理
- [x] 日付変換（YYMMDD → YYYY/MM/DD）
- [x] プレビュー生成（先頭5件）
- [x] エラーハンドリング（カスタム例外、個人情報マスキング）
- [x] 単体テスト（正常系・異常系、カバレッジ80%以上）

## 主要な改善点（project-orchestrator 指摘事項対応）
1. **承認条件1**: CSVサンプル確認プロセスを事前確認項目に追加
2. **承認条件2**: データ構造を完全化（user, payment_method, note, year, month, month_str フィールド追加）
3. **承認条件3**: ファイルパスバリデーション関数を追加（パストラバーサル対策）
4. **承認条件4**: モジュール名を csv_parser.py に統一
5. **承認条件5**: 金額のカンマ除去処理を追加
6. **中優先度改善**: CP932フォールバック処理を追加
7. **中優先度改善**: 特殊文字テストデータ（髙、﨑、①、②）を追加
8. **低優先度改善**: ログ出力ガイドライン（個人情報マスキング）を明示
9. **低優先度改善**: カバレッジ目標（80%以上）を設定

## テスト結果
- 単体テスト: 全件PASS
- カバレッジ: 80%以上
- パフォーマンステスト: 1000件処理 < 30秒

## 関連ドキュメント
- `.claude/02_backend/05_csv_record_definition.md`
- `.claude/02_backend/02_backend_modules_spec.md`
- `.claude/09_test/00_backend_test_specification.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## 6. 想定される問題と対処法

### 6.1 エンコーディング検出の問題

**問題**: chardet の検出精度が低く、誤ったエンコーディングを返す可能性

**対処法**:
1. 検出信頼度（confidence）が0.7未満の場合はCP932フォールバック **【修正済み】**
2. ユーザーに手動でエンコーディングを指定できるオプションを提供（将来的な拡張）
3. Shift_JIS の別名（cp932, ms932）も考慮した処理 **【修正済み】**
4. ログに検出結果の詳細（confidence, encoding）を出力

**代替案**:
- 最初に Shift_JIS で試み、失敗したら CP932、さらに失敗したら UTF-8 で試すフォールバック戦略

### 6.2 CSV形式のバリエーション

**問題**: イオンカードのCSV形式が予告なく変更される可能性

**対処法**:
1. **【重要】実際のCSVサンプルをユーザーから提供してもらう** **【修正済み】**
2. 列番号をハードコーディングせず、定数として定義
3. CSV構造のバリデーション関数を実装（列数チェック、ヘッダー検証）
4. エラーメッセージに具体的な行番号・列番号を含める
5. ログにCSVの先頭3行を出力（デバッグ用、個人情報マスキング）

**代替案**:
- 設定ファイルで列番号をカスタマイズできる仕組み（将来的な拡張）

### 6.3 日付の境界値問題

**問題**: 2050年以降のデータが発生した場合の処理

**対処法**:
1. 現在は YY が 00-49 → 2000年代、50-99 → 1900年代 のロジック
2. 将来的には設定ファイルで境界年を調整可能にする
3. ログに変換前後の日付を出力

**代替案**:
- システム日付を基準に相対的な判定を行う（現在年から±50年）

### 6.4 大容量ファイルのメモリ使用量

**問題**: 10MBのファイルを全てメモリに読み込むとメモリ不足の可能性

**対処法**:
1. pandas の `chunksize` パラメータを使用してストリーミング処理
2. 不要なデータは早期に除外（8行目以前のヘッダー行）
3. プレビュー生成時は先頭5件のみをメモリに保持

**代替案**:
- ファイルサイズ上限を5MBに引き下げ（性能要件と相談）

### **【修正】6.5 特殊文字・機種依存文字の問題（CP932対応済み）**

**問題**: Shift_JIS に含まれる特殊文字（髙、﨑、①、②など）が文字化けする可能性

**対処法**:
1. **CP932エンコーディングを優先的に使用** **【修正済み】**
2. エンコーディング変換時に `errors='strict'` を使用（エラーを明示的に検出）
3. 文字化けが発生した場合は詳細なエラーメッセージを表示
4. **テストデータに特殊文字（髙、﨑、①、②）を含めて事前検証** **【修正済み】**

**代替案**:
- CP932（Windows-31J）を最初に試行するフォールバック戦略 **【実装済み】**

### **【修正】6.6 CSVサンプルデータの準備（承認条件1対応）**

**問題**: 実際のイオンカード明細CSVが手元にない場合、テストデータの作成が困難

**対処法**:
1. **【最優先】ユーザーに実際のCSVサンプル（個人情報削除済み）の提供を依頼** **【修正済み】**
2. `.claude/02_backend/05_csv_record_definition.md` を参照してサンプルを作成
3. 最小限のテストデータで開発を進め、後で実データで検証
4. CSVサンプル提供時に以下を確認:
   - ヘッダー行数
   - 列番号の対応
   - 金額フォーマット（カンマ区切りの有無）
   - 特殊文字の使用状況
   - 備考欄の位置（列7 or 8）

**想定される追加確認事項**:
- CSVの実際の構造（ヘッダー行数、列数）
- 金額列のフォーマット（カンマ区切りの有無） **【対応済み】**
- 店舗名の文字数上限
- 特殊文字の使用状況 **【対応済み】**

### 6.7 依存パッケージのバージョン問題

**問題**: pandas や chardet のバージョンによって動作が異なる可能性

**対処法**:
1. `requirements.txt` に具体的なバージョンを指定
2. 開発時のバージョンをドキュメントに記録
3. CI/CD 環境で異なるバージョンでのテストを実施（将来的）

**確認事項**:
- 現在の `requirements.txt` の内容確認
- pandas 2.0+ の互換性確認

### 6.8 Windows/Mac/Linux のパス問題

**問題**: OS によってパス区切り文字が異なる（`/` vs `\`）

**対処法**:
1. `pathlib.Path` を使用してOSに依存しないパス操作 **【実装済み】**
2. 文字列結合ではなく、`Path` オブジェクトの `/` 演算子を使用

---

## **【修正】7. チェックリスト（CSVサンプル確認追加、モジュール名変更）**

### 7.1 実装前チェック
- [ ] `.claude/02_backend/05_csv_record_definition.md` を熟読
- [ ] `.claude/02_backend/02_backend_modules_spec.md` を熟読（csv_parser.py 仕様確認）
- [ ] `.claude/02_backend/01_backend_api_routes.md` を熟読
- [ ] `.claude/06_security/security_requirements.md` を熟読
- [ ] `.claude/09_test/00_backend_test_specification.md` を熟読
- [ ] `modules/` ディレクトリの存在確認
- [ ] `requirements.txt` の内容確認
- [ ] Python 仮想環境のアクティベート確認
- [ ] **【重要】ユーザーに実際のイオンカード明細CSVサンプル（個人情報削除済み）の提供を依頼** **【新規】**
- [ ] CSVサンプルの構造確認（列番号、ヘッダー行数、金額フォーマット、特殊文字） **【新規】**

### 7.2 実装中チェック
- [ ] カスタム例外クラスの定義完了（PathValidationError 含む）
- [ ] **【新規】** `validate_file_path()` 実装完了
- [ ] `detect_encoding()` 実装完了（CP932フォールバック対応）
- [ ] `validate_file_size()` 実装完了
- [ ] `read_csv_file()` 実装完了（CP932対応）
- [ ] `is_detail_row()` 実装完了
- [ ] **【修正】** `extract_detail_data()` 実装完了（全フィールド、カンマ除去対応）
- [ ] `convert_date_format()` 実装完了
- [ ] `extract_month_number()` 実装完了
- [ ] `generate_preview()` 実装完了
- [ ] **【修正】** `process_csv_file()` 実装完了（year, month, month_str 追加）
- [ ] 全関数に型ヒント（type hints）を追加
- [ ] 全関数にdocstringを追加（日本語または英語）
- [ ] PEP 8 準拠の確認（flake8 または pylint 使用）

### **【修正】7.3 テスト実装チェック**
- [ ] **【新規】** `test_validate_file_path.py` 実装完了（パストラバーサルテスト）
- [ ] `test_detect_encoding.py` 実装完了（CP932フォールバックテスト追加）
- [ ] `test_validate_file_size.py` 実装完了
- [ ] `test_read_csv_file.py` 実装完了（特殊文字テスト追加）
- [ ] `test_is_detail_row.py` 実装完了
- [ ] **【修正】** `test_extract_detail_data.py` 実装完了（全フィールド、カンマ除去テスト追加）
- [ ] `test_convert_date_format.py` 実装完了（境界値テスト含む）
- [ ] `test_extract_month_number.py` 実装完了
- [ ] `test_generate_preview.py` 実装完了
- [ ] **【修正】** `test_process_csv_file.py` 実装完了（全フィールド対応）
- [ ] 統合テスト実装完了
- [ ] パフォーマンステスト実装完了（1000件・30秒以内）
- [ ] **【新規】** カバレッジ計測実施（80%以上を確認）
- [ ] 全テストがPASSすることを確認

### **【修正】7.4 セキュリティチェック**
- [ ] **【新規】** ファイルパスのバリデーション実装（validate_file_path）
- [ ] ファイルサイズ上限チェック実装（10MB）
- [ ] エンコーディングエラーの安全な処理
- [ ] CSVインジェクション対策の確認
- [ ] **【新規】** 個人情報のログ出力マスキング実装（備考欄除外）
- [ ] エラーメッセージに機密情報が含まれないことを確認

### 7.5 ドキュメント・Git チェック
- [ ] `.claude/00_project/08_dev_step.md` の Step 2.1 を完了に更新
- [ ] コード内のコメント・docstring が適切
- [ ] テストデータの作成完了（特殊文字データ、カンマ区切りデータ追加）
- [ ] README や CLAUDE.md の更新が必要か確認
- [ ] Git ステータス確認（不要なファイルがstageされていないか）
- [ ] **【修正】** ファイル名が `csv_parser.py` であることを確認
- [ ] コミットメッセージが明確で具体的か確認
- [ ] プッシュ前にローカルで全テストを実行
- [ ] プッシュ完了の確認

### 7.6 最終確認
- [ ] コードレビュー（自己レビュー）
- [ ] パフォーマンス要件を満たしているか確認（1000件・30秒以内）
- [ ] エラーハンドリングが適切か確認
- [ ] ユーザー向けエラーメッセージが日本語で分かりやすいか確認
- [ ] **【新規】** ログ出力が個人情報マスキング方針に準拠しているか確認
- [ ] ログ出力が開発者にとって有用か確認
- [ ] **【新規】** カバレッジ目標（80%以上）を達成しているか確認
- [ ] 次のステップ（Step 2.2: Google Sheets API連携）への準備完了

---

## 補足: 実装順序の推奨フロー

この作業計画に従って実装する場合、以下の順序で進めることを推奨します:

1. **Phase 1: 基盤構築**（コミット1）
   - **【重要】ユーザーにCSVサンプル提供を依頼**
   - カスタム例外クラス定義（PathValidationError 追加）
   - 定数定義
   - **【新規】** `validate_file_path()`
   - `detect_encoding()` **【修正: CP932フォールバック対応】**
   - `validate_file_size()`
   - 単体テスト作成・実行

2. **Phase 2: CSV読み込み**（コミット2）
   - `read_csv_file()` **【修正: CP932対応】**
   - `is_detail_row()`
   - `extract_detail_data()` **【修正: 全フィールド、カンマ除去対応】**
   - 単体テスト作成・実行（特殊文字テスト、カンマ除去テスト追加）

3. **Phase 3: 日付変換**（コミット3）
   - `convert_date_format()`
   - `extract_month_number()`
   - 単体テスト作成・実行（境界値テスト重視）

4. **Phase 4: 統合処理**（コミット4）
   - `generate_preview()`
   - `process_csv_file()` **【修正: year, month, month_str 追加】**
   - 統合テスト作成・実行

5. **Phase 5: テスト強化**（コミット5）
   - パフォーマンステスト
   - 異常系テストの追加
   - **【新規】** カバレッジ計測・確認（80%以上）

6. **Phase 6: 仕上げ**（コミット6）
   - テストデータ整備（特殊文字データ、カンマ区切りデータ追加）
   - ドキュメント更新
   - 最終確認

この順序により、段階的に機能を追加しながら常にテストでき、問題を早期に発見できます。

---

## 付録: project-orchestrator 承認条件チェックリスト

### 承認条件1: 実際のCSVサンプル確認
- [x] 事前確認項目「1.4 CSVサンプル確認」に追加
- [x] CSV構造確認項目を詳細に記載（列番号、ヘッダー行数、金額フォーマット、特殊文字）
- [x] 実装前チェックリストにCSVサンプル提供依頼を追加

### 承認条件2: データ構造を完全化
- [x] `extract_detail_data()` で列1（user）、列3（payment_method）、列7/8（note）を抽出
- [x] `process_csv_file()` の返り値に year, month, month_str, user, payment_method, note を含める
- [x] データ構造例を詳細に記載（3.5.3）

### 承認条件3: ファイルパスバリデーション関数を追加
- [x] `validate_file_path()` 関数を追加（3.1.1）
- [x] 関数一覧に `validate_file_path()` を追加（2.2）
- [x] パストラバーサル対策を実装
- [x] テストケースに `test_validate_file_path.py` を追加（4.2.1）

### 承認条件4: モジュール名を統一
- [x] モジュール名を `csv_processor.py` → `csv_parser.py` に変更（2.1）
- [x] すべての記述で `csv_parser.py` に統一
- [x] チェックリストにファイル名確認を追加（7.5）

### 承認条件5: 金額のカンマ処理を追加
- [x] `extract_detail_data()` でカンマ除去処理を追加（3.2.2）
- [x] テストケースに金額カンマ区切りテストを追加（4.1.3, 4.2.6）

### 中優先度改善
- [x] CP932フォールバック処理を追加（3.1.2）
- [x] 特殊文字テストデータを追加（4.1.2）

### 低優先度改善
- [x] ログ出力ガイドライン（個人情報マスキング）を明示（3.5.2）
- [x] カバレッジ目標（80%以上）を設定（4.3.2）

---

**修正版作業計画の完成**

この修正版作業計画は、project-orchestrator からの5つの承認条件をすべて満たし、中優先度・低優先度の改善提案も可能な限り反映しています。前回の作業計画の優れた点（詳細なテスト計画、Git戦略、6段階のコミット計画など）は維持しつつ、指摘事項を完全に統合しました。
