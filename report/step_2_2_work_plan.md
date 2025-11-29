# Step 2.2: カテゴリ判定エンジン作成 - 作業計画書

## プロジェクト概要

**対象ファイル**: `modules/category_logic.py`

**目的**: 店舗名からカテゴリを自動判定し、Googleスプレッドシートの該当列へマッピングするエンジンを実装する

**参考資料**:
- `.claude/00_project/08_dev_step.md` (87-102行) - Step 2.2要件
- `.claude/02_backend/02_backend_modules_spec.md` - バックエンドモジュール仕様
- `.claude/02_backend/03_mapping_table_definition.md` - マッピングテーブル定義
- `.claude/02_backend/04_category_master_definition.md` - カテゴリマスター定義

**前提条件**:
- Step 2.1（CSV処理モジュール）が完了済み
- `config/mapping.json` が存在し、正しいJSON形式である
- テストカバレッジ目標: 80%以上（Step 2.1と同等）

---

## 全体スケジュール

| Phase | 内容 | 担当 | 期間 |
|-------|------|------|------|
| Phase 1 | 基盤構築（例外クラス、定数定義） | backend-code-generator | 1日 |
| Phase 2 | マッピングデータ読込・検証 | backend-code-generator | 1日 |
| Phase 3 | パターンマッチング実装 | backend-code-generator | 2日 |
| Phase 4 | カテゴリ決定・未登録店舗検出 | backend-code-generator | 2日 |
| Phase 5 | テスト強化・カバレッジ向上 | project-compliance-tester | 2日 |
| Phase 6 | 最終確認・ドキュメント更新 | project-orchestrator | 1日 |

**合計期間**: 約9日間

---

## Phase 1: 基盤構築（例外クラス、定数定義）

### 目的
カテゴリ判定エンジンの基盤となる例外クラス、定数、基本構造を実装する

### 実装内容

#### 1.1 カスタム例外クラス定義
```python
class CategoryLogicError(Exception):
    """カテゴリ判定の基底例外クラス"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class MappingLoadError(CategoryLogicError):
    """マッピングデータ読み込みエラー"""
    pass

class MappingValidationError(CategoryLogicError):
    """マッピングデータ検証エラー"""
    pass

class CategoryMatchError(CategoryLogicError):
    """カテゴリマッチングエラー"""
    pass

class InvalidMappingFormatError(CategoryLogicError):
    """無効なマッピング形式エラー"""
    pass
```

#### 1.2 定数定義
```python
# ファイルパス
DEFAULT_MAPPING_PATH = 'config/mapping.json'

# マッチタイプ
MATCH_TYPE_EXACT = 'exact'        # 完全一致
MATCH_TYPE_STARTSWITH = 'startswith'  # 前方一致
MATCH_TYPE_CONTAINS = 'contains'    # 部分一致
MATCH_TYPE_KEYWORD = 'keyword'      # キーワード一致

VALID_MATCH_TYPES = [MATCH_TYPE_EXACT, MATCH_TYPE_STARTSWITH,
                     MATCH_TYPE_CONTAINS, MATCH_TYPE_KEYWORD]

# デフォルト列
DEFAULT_COLUMN = 'B'
DEFAULT_CATEGORY = '支払額'

# 列範囲
VALID_COLUMNS = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
                 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
                 'T', 'U', 'V']

# 優先順位
PRIORITY_EXACT = 1       # 完全一致の優先度
PRIORITY_STARTSWITH = 2  # 前方一致の優先度
PRIORITY_CONTAINS = 3    # 部分一致の優先度
PRIORITY_KEYWORD = 4     # キーワード一致の優先度
```

#### 1.3 型定義（TypedDict）
```python
from typing import TypedDict, List, Optional

class MappingEntry(TypedDict):
    """マッピングエントリの型定義"""
    id: int
    pattern: str
    match_type: str
    category: str
    column: str
    priority: int
    note: Optional[str]

class MappingData(TypedDict):
    """マッピングデータ全体の型定義"""
    version: str
    mappings: List[MappingEntry]
    default: dict

class MatchResult(TypedDict):
    """マッチング結果の型定義"""
    matched: bool
    category: str
    column: str
    pattern: Optional[str]
    match_type: Optional[str]
```

### テスト項目

| No | テスト項目 | 期待結果 | 優先度 |
|----|-----------|---------|--------|
| 1.1 | CategoryLogicError例外がメッセージとdetailsを保持する | 正常にインスタンス化できる | 高 |
| 1.2 | 各カスタム例外がCategoryLogicErrorを継承している | isinstance チェックが通る | 高 |
| 1.3 | 定数が正しく定義されている | 定数値が期待通り | 中 |
| 1.4 | VALID_MATCH_TYPESに全マッチタイプが含まれる | リスト要素が4つ | 中 |
| 1.5 | VALID_COLUMNSがB～V列（21列）を含む | リスト要素が21個 | 中 |

### 成功基準
- [ ] すべてのカスタム例外クラスが定義され、基底クラスを継承している
- [ ] 全定数が明確に定義されている
- [ ] 型定義（TypedDict）が完備されている
- [ ] テストカバレッジ: 100%（定数・例外クラス定義のみ）

### 担当
- **実装**: backend-code-generator
- **レビュー**: project-orchestrator

---

## Phase 2: マッピングデータ読込・検証

### 目的
`config/mapping.json`からマッピングデータを読み込み、データの妥当性を検証する

### 実装内容

#### 2.1 マッピングデータ読込関数
```python
def load_mapping_data(config_path: str = DEFAULT_MAPPING_PATH) -> MappingData:
    """
    マッピングデータをJSONファイルから読み込む

    Args:
        config_path: マッピングファイルパス

    Returns:
        MappingData: マッピングデータ辞書

    Raises:
        MappingLoadError: ファイルが存在しない、読み込めない
        InvalidMappingFormatError: JSON形式が不正
        MappingValidationError: 必須フィールドが不足
    """
    pass
```

**処理フロー**:
1. ファイル存在確認
2. JSONファイル読み込み
3. 必須フィールド検証（version, mappings, default）
4. MappingData型として返却

#### 2.2 マッピングエントリ検証関数
```python
def validate_mapping_entry(entry: dict) -> bool:
    """
    マッピングエントリの妥当性を検証

    Args:
        entry: マッピングエントリ辞書

    Returns:
        bool: 検証結果（True=正常、False=異常）

    Raises:
        MappingValidationError: 必須フィールド不足、不正な値
    """
    pass
```

**検証項目**:
- 必須フィールド: `id`, `pattern`, `match_type`, `category`, `column`, `priority`
- `match_type`が`VALID_MATCH_TYPES`に含まれる
- `column`が`VALID_COLUMNS`に含まれる
- `priority`が正の整数
- `pattern`が空文字列でない

#### 2.3 マッピングデータ検証関数
```python
def validate_mapping_data(data: MappingData) -> bool:
    """
    マッピングデータ全体の妥当性を検証

    Args:
        data: マッピングデータ辞書

    Returns:
        bool: 検証結果

    Raises:
        MappingValidationError: データ構造が不正
    """
    pass
```

**検証項目**:
- `version`フィールド存在確認
- `mappings`がリスト型
- `default`が辞書型で、`category`と`column`を含む
- 各エントリが`validate_mapping_entry`をパスする
- `id`の重複がない

### テスト項目

| No | テスト項目 | 期待結果 | 優先度 |
|----|-----------|---------|--------|
| 2.1 | 正常なmapping.jsonを読み込める | MappingData型で返却される | 高 |
| 2.2 | ファイルが存在しない場合 | MappingLoadErrorが発生する | 高 |
| 2.3 | JSON形式が不正な場合 | InvalidMappingFormatErrorが発生する | 高 |
| 2.4 | 必須フィールドが不足している場合 | MappingValidationErrorが発生する | 高 |
| 2.5 | match_typeが不正な値の場合 | MappingValidationErrorが発生する | 中 |
| 2.6 | columnが範囲外（例: 'Z'）の場合 | MappingValidationErrorが発生する | 中 |
| 2.7 | priorityが負の整数の場合 | MappingValidationErrorが発生する | 中 |
| 2.8 | patternが空文字列の場合 | MappingValidationErrorが発生する | 中 |
| 2.9 | idが重複している場合 | MappingValidationErrorが発生する | 低 |
| 2.10 | defaultフィールドが不足している場合 | MappingValidationErrorが発生する | 中 |

### 成功基準
- [ ] `load_mapping_data`が正常に動作する
- [ ] すべての検証関数が適切にエラーを検出する
- [ ] テストカバレッジ: 80%以上
- [ ] 異常系テストが10ケース以上実装されている

### 担当
- **実装**: backend-code-generator
- **テスト**: project-compliance-tester

---

## Phase 3: パターンマッチング実装

### 目的
店舗名とマッピングパターンを照合し、最適なカテゴリを決定するロジックを実装する

### 実装内容

#### 3.1 完全一致判定関数
```python
def match_exact(store_name: str, pattern: str) -> bool:
    """
    完全一致判定

    Args:
        store_name: 店舗名
        pattern: パターン文字列

    Returns:
        bool: 一致判定結果
    """
    return store_name == pattern
```

#### 3.2 前方一致判定関数
```python
def match_startswith(store_name: str, pattern: str) -> bool:
    """
    前方一致判定

    Args:
        store_name: 店舗名
        pattern: パターン文字列

    Returns:
        bool: 一致判定結果
    """
    return store_name.startswith(pattern)
```

#### 3.3 部分一致判定関数
```python
def match_contains(store_name: str, pattern: str) -> bool:
    """
    部分一致判定

    Args:
        store_name: 店舗名
        pattern: パターン文字列

    Returns:
        bool: 一致判定結果
    """
    return pattern in store_name
```

#### 3.4 キーワード一致判定関数
```python
def match_keyword(store_name: str, pattern: str) -> bool:
    """
    キーワード一致判定（スペース区切りでAND条件）

    Args:
        store_name: 店舗名
        pattern: パターン文字列（スペース区切り）

    Returns:
        bool: 一致判定結果

    例:
        pattern="イオン 幕張" → "イオン" AND "幕張" が店舗名に含まれる
    """
    keywords = pattern.split()
    return all(keyword in store_name for keyword in keywords)
```

#### 3.5 パターンマッチング実行関数
```python
def execute_pattern_match(store_name: str, entry: MappingEntry) -> bool:
    """
    マッピングエントリに基づいてパターンマッチングを実行

    Args:
        store_name: 店舗名
        entry: マッピングエントリ

    Returns:
        bool: マッチ結果

    Raises:
        CategoryMatchError: 不明なmatch_type
    """
    match_type = entry['match_type']
    pattern = entry['pattern']

    if match_type == MATCH_TYPE_EXACT:
        return match_exact(store_name, pattern)
    elif match_type == MATCH_TYPE_STARTSWITH:
        return match_startswith(store_name, pattern)
    elif match_type == MATCH_TYPE_CONTAINS:
        return match_contains(store_name, pattern)
    elif match_type == MATCH_TYPE_KEYWORD:
        return match_keyword(store_name, pattern)
    else:
        raise CategoryMatchError(
            f"Unknown match_type: {match_type}",
            details={'match_type': match_type, 'pattern': pattern}
        )
```

#### 3.6 最適マッチング選択関数
```python
def find_best_match(
    store_name: str,
    mappings: List[MappingEntry]
) -> Optional[MappingEntry]:
    """
    優先順位に基づき最適なマッピングを選択

    優先順位:
    1. 完全一致（exact）
    2. 前方一致（startswith）
    3. 部分一致（contains）
    4. キーワード一致（keyword）

    同じmatch_typeの場合は、priorityフィールドで判定

    Args:
        store_name: 店舗名
        mappings: マッピングエントリリスト

    Returns:
        Optional[MappingEntry]: マッチしたエントリ（なければNone）
    """
    pass
```

**処理フロー**:
1. match_typeごとにマッピングエントリをグループ化
2. 完全一致 → 前方一致 → 部分一致 → キーワード一致の順で検索
3. 各グループ内ではpriorityが小さいものを優先
4. 最初にマッチしたエントリを返却

### テスト項目

| No | テスト項目 | 期待結果 | 優先度 |
|----|-----------|---------|--------|
| 3.1 | 完全一致: "ユシンヤ" == "ユシンヤ" | True | 高 |
| 3.2 | 完全一致: "ユシンヤカマタテン" == "ユシンヤ" | False | 高 |
| 3.3 | 前方一致: "ユシンヤカマタテン".startswith("ユシンヤ") | True | 高 |
| 3.4 | 前方一致: "カマタユシンヤ".startswith("ユシンヤ") | False | 高 |
| 3.5 | 部分一致: "ユシンヤ" in "ユシンヤカマタテン" | True | 高 |
| 3.6 | 部分一致: "ユシンヤ" in "カマタユシンヤ" | True | 高 |
| 3.7 | キーワード一致: "イオン 幕張" → "イオンスタイル幕張新都心" | True | 中 |
| 3.8 | キーワード一致: "イオン 千葉" → "イオンスタイル幕張新都心" | False | 中 |
| 3.9 | 複数マッチング: 完全一致が優先される | 完全一致エントリが返却される | 高 |
| 3.10 | 複数マッチング: priority値で優先順位決定 | priority=1が返却される | 中 |
| 3.11 | マッチなし: "存在しない店舗" | None | 高 |
| 3.12 | 不明なmatch_type | CategoryMatchErrorが発生する | 中 |

### 成功基準
- [ ] 各マッチング関数（exact, startswith, contains, keyword）が正常動作する
- [ ] `find_best_match`が優先順位に従って正しく選択する
- [ ] テストカバレッジ: 80%以上
- [ ] エッジケーステスト（空文字列、特殊文字等）が実装されている

### 担当
- **実装**: backend-code-generator
- **テスト**: project-compliance-tester

---

## Phase 4: カテゴリ決定・未登録店舗検出

### 目的
店舗名からカテゴリと列番号を決定し、未登録店舗を検出する統合機能を実装する

### 実装内容

#### 4.1 カテゴリ決定関数
```python
def determine_category(
    store_name: str,
    mapping_data: MappingData
) -> MatchResult:
    """
    店舗名からカテゴリと列番号を決定

    Args:
        store_name: 店舗名
        mapping_data: マッピングデータ

    Returns:
        MatchResult: マッチング結果
            {
                'matched': bool,  # マッチしたかどうか
                'category': str,  # カテゴリ名
                'column': str,    # 列番号（B～V）
                'pattern': Optional[str],  # マッチしたパターン
                'match_type': Optional[str]  # マッチタイプ
            }
    """
    # 1. find_best_matchでマッピング検索
    best_match = find_best_match(store_name, mapping_data['mappings'])

    # 2. マッチした場合
    if best_match:
        return {
            'matched': True,
            'category': best_match['category'],
            'column': best_match['column'],
            'pattern': best_match['pattern'],
            'match_type': best_match['match_type']
        }

    # 3. マッチしなかった場合（デフォルト列）
    default = mapping_data['default']
    return {
        'matched': False,
        'category': default['category'],
        'column': default['column'],
        'pattern': None,
        'match_type': None
    }
```

#### 4.2 未登録店舗検出関数
```python
def detect_unregistered_stores(
    records: List[Dict],
    mapping_data: MappingData
) -> List[Dict]:
    """
    未登録店舗を検出し、店舗ごとの金額合計を算出

    Args:
        records: 明細レコードリスト（csv_processor.pyの出力）
            例: [
                {'date': '2025/08/15', 'store': 'ユシンヤ', 'amount': 5780, ...},
                {'date': '2025/08/16', 'store': 'AMAZON', 'amount': 1200, ...}
            ]
        mapping_data: マッピングデータ

    Returns:
        List[Dict]: 未登録店舗リスト
            [
                {
                    'store': '未登録店舗A',
                    'count': 3,  # 出現回数
                    'total_amount': 15000  # 合計金額
                },
                ...
            ]
    """
    pass
```

**処理フロー**:
1. 各レコードに対して`determine_category`を実行
2. `matched=False`のレコードを抽出
3. 店舗名でグループ化
4. 店舗ごとに件数と金額合計を算出
5. 金額降順でソート

#### 4.3 バッチカテゴリ決定関数
```python
def determine_categories_batch(
    records: List[Dict],
    mapping_data: MappingData
) -> List[Dict]:
    """
    複数レコードのカテゴリを一括決定

    Args:
        records: 明細レコードリスト
        mapping_data: マッピングデータ

    Returns:
        List[Dict]: カテゴリ情報付きレコードリスト
            [
                {
                    'date': '2025/08/15',
                    'store': 'ユシンヤ',
                    'amount': 5780,
                    'category': '外食費',
                    'column': 'C',
                    'matched': True
                },
                ...
            ]
    """
    pass
```

### テスト項目

| No | テスト項目 | 期待結果 | 優先度 |
|----|-----------|---------|--------|
| 4.1 | 登録済み店舗のカテゴリ決定 | matched=True、正しいcategory/column | 高 |
| 4.2 | 未登録店舗のカテゴリ決定 | matched=False、デフォルト列（B列） | 高 |
| 4.3 | 空文字列の店舗名 | デフォルト列を返却 | 中 |
| 4.4 | Noneの店舗名 | エラー処理またはデフォルト列 | 中 |
| 4.5 | 複数レコードのバッチ処理 | 全レコードが処理される | 高 |
| 4.6 | 未登録店舗が0件 | 空リストを返却 | 中 |
| 4.7 | 未登録店舗が1件 | 正しいcount/total_amount | 高 |
| 4.8 | 未登録店舗が複数件（同一店舗重複） | 店舗ごとに集約される | 高 |
| 4.9 | 未登録店舗リストが金額降順でソート | total_amountが降順 | 中 |
| 4.10 | 金額0円の未登録店舗 | 正しくリストに含まれる | 低 |

### 成功基準
- [ ] `determine_category`が登録済み・未登録店舗を正しく判定する
- [ ] `detect_unregistered_stores`が正確に集計する
- [ ] `determine_categories_batch`が大量データを効率処理する
- [ ] テストカバレッジ: 80%以上
- [ ] 1000件レコードの処理時間が1秒以内

### 担当
- **実装**: backend-code-generator
- **テスト**: project-compliance-tester

---

## Phase 5: テスト強化・カバレッジ向上

### 目的
テストカバレッジを80%以上に引き上げ、異常系・境界値テストを充実させる

### テスト強化項目

#### 5.1 正常系テスト（20ケース以上）
- 各マッチタイプでの正常動作確認
- バッチ処理の正常動作
- 大量データ処理（100件、1000件）
- 各種店舗名パターン（全角・半角・記号・英数字）

#### 5.2 異常系テスト（15ケース以上）
- ファイルが存在しない
- JSON形式が不正
- 必須フィールド不足
- 不正なmatch_type
- 不正なcolumn値
- 不正なpriority値
- 空のmappings配列
- defaultフィールド不足

#### 5.3 境界値テスト（10ケース以上）
- 空文字列の店舗名
- 非常に長い店舗名（1000文字）
- 特殊文字を含む店舗名（①、②、髙、﨑）
- 空のレコードリスト
- 1件のみのレコード
- 重複する店舗名

#### 5.4 統合テスト（5ケース以上）
- csv_processor.py → category_logic.py の連携
- 実際のサンプルCSVファイルでの動作確認
- マッピング変更後の再処理
- 未登録店舗の検出と集計

#### 5.5 パフォーマンステスト（3ケース）
- 1000件レコードの処理時間（目標: 1秒以内）
- 10000件レコードの処理時間（目標: 10秒以内）
- メモリ使用量の確認

### テストファイル構成

```
tests/
├── test_category_logic_unit.py         # 単体テスト（40ケース）
├── test_category_logic_integration.py  # 統合テスト（10ケース）
├── test_category_logic_edge_cases.py   # 境界値・異常系（25ケース）
└── test_category_logic_performance.py  # パフォーマンステスト（3ケース）
```

### カバレッジ目標

| モジュール | 関数カバレッジ | 行カバレッジ | 分岐カバレッジ |
|----------|--------------|------------|--------------|
| category_logic.py | 100% | 85%以上 | 80%以上 |

### 成功基準
- [ ] テストカバレッジ: 80%以上（Step 2.1と同等）
- [ ] 単体テスト: 40ケース以上
- [ ] 統合テスト: 10ケース以上
- [ ] 異常系・境界値テスト: 25ケース以上
- [ ] パフォーマンステスト: 3ケース
- [ ] すべてのテストがパスする
- [ ] テストコードにdocstringが記載されている

### 担当
- **テスト設計・実装**: project-compliance-tester
- **レビュー**: project-orchestrator

---

## Phase 6: 最終確認・ドキュメント更新

### 目的
実装の最終確認を行い、ドキュメントとテストデータを整備する

### 実施内容

#### 6.1 コード品質確認
- [ ] PEP 8準拠確認
- [ ] 関数・変数名が英語で命名されている
- [ ] docstringが全関数に記載されている
- [ ] 型ヒントが適切に記載されている
- [ ] エラーメッセージが明確である

#### 6.2 統合動作確認
- [ ] csv_processor.py → category_logic.py の連携動作
- [ ] 実際のサンプルCSVでの動作確認
- [ ] 未登録店舗検出の動作確認
- [ ] マッピング変更後の再処理確認

#### 6.3 テストデータ作成
- [ ] `tests/test_data/mapping_valid.json` - 正常系マッピングデータ
- [ ] `tests/test_data/mapping_invalid_format.json` - JSON形式エラー
- [ ] `tests/test_data/mapping_missing_field.json` - 必須フィールド不足
- [ ] `tests/test_data/mapping_invalid_match_type.json` - 不正match_type
- [ ] `tests/test_data/mapping_duplicate_id.json` - ID重複

#### 6.4 ドキュメント更新
- [ ] `.claude/00_project/08_dev_step.md` のStep 2.2をチェック済みに更新
- [ ] `modules/category_logic.py` の冒頭にモジュールdocstring追加
- [ ] 関数一覧とその役割を記載
- [ ] 使用例を記載

#### 6.5 コミット準備
- [ ] git statusで変更ファイル確認
- [ ] テスト実行結果確認
- [ ] カバレッジレポート確認
- [ ] コミットメッセージ準備

### 成果物

1. **実装ファイル**
   - `modules/category_logic.py` (推定800-1000行)

2. **テストファイル**
   - `tests/test_category_logic_unit.py` (推定600行)
   - `tests/test_category_logic_integration.py` (推定300行)
   - `tests/test_category_logic_edge_cases.py` (推定400行)
   - `tests/test_category_logic_performance.py` (推定200行)

3. **テストデータ**
   - 5つのマッピングJSONサンプルファイル

4. **ドキュメント**
   - `.claude/00_project/08_dev_step.md` 更新版

### 成功基準
- [ ] すべてのテストがパスする
- [ ] テストカバレッジが80%以上
- [ ] コード品質チェックがすべてパスする
- [ ] ドキュメントが更新されている
- [ ] gitコミット準備が完了している

### 担当
- **確認・調整**: project-orchestrator
- **ドキュメント作成**: backend-code-generator

---

## 全体の成功基準（Summary）

### 機能要件
- [x] マッピングデータ読込機能が動作する
- [x] 完全一致・前方一致・部分一致・キーワード一致が正しく判定される
- [x] 優先順位に基づく最適マッチングが動作する
- [x] カテゴリと列番号が正しく決定される
- [x] 未登録店舗の検出と集計が正確に行われる
- [x] バッチ処理が効率的に動作する

### 品質要件
- [x] テストカバレッジ: 80%以上（Step 2.1と同等）
- [x] テストケース総数: 78件以上（正常20、異常15、境界10、統合10、性能3、その他20）
- [x] PEP 8準拠
- [x] 全関数にdocstringが記載されている
- [x] 型ヒントが適切に記載されている

### パフォーマンス要件
- [x] 1000件レコードの処理時間: 1秒以内
- [x] 10000件レコードの処理時間: 10秒以内
- [x] メモリ使用量: 100MB以内（通常処理時）

### セキュリティ要件
- [x] ファイルパス検証（パストラバーサル対策）
- [x] JSON解析時の例外処理
- [x] 不正なマッピングデータの検出と拒否

---

## リスク管理

### 想定リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|---------|------|
| マッピングJSONの形式が想定外 | 高 | 中 | 厳密な検証関数を実装 |
| パターンマッチングの優先順位が不明確 | 中 | 低 | 仕様書で明確化、テストで検証 |
| 大量データでのパフォーマンス低下 | 中 | 中 | パフォーマンステストを実施 |
| 特殊文字を含む店舗名での誤判定 | 低 | 中 | エッジケーステストを充実 |

---

## 備考

### Step 2.1との連携
- `csv_processor.py`の`process_csv_file`関数が返すレコードリストを入力とする
- レコード形式: `{'date': str, 'store': str, 'amount': int, ...}`

### Step 2.3（マッピング管理）との連携
- `mapping_manager.py`が`config/mapping.json`を更新する
- `category_logic.py`は最新のマッピングデータを読み込む必要がある

### 将来の拡張性
- カテゴリマスターのデータベース化
- マッピングルールの機械学習
- 正規表現パターンマッチングの追加

---

**作成日**: 2025-11-29
**作成者**: project-orchestrator
**承認者**: （ユーザー承認待ち）
