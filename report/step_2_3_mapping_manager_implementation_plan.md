# Step 2.3: マッピング管理モジュール実装計画書

**作成日**: 2025-12-16
**対象モジュール**: `modules/mapping_manager.py`
**実装ステータス**: 未実装（計画フェーズ）

---

## 目次

1. [モジュール設計](#1-モジュール設計)
2. [機能要件](#2-機能要件)
3. [実装計画](#3-実装計画)
4. [技術仕様](#4-技術仕様)
5. [テスト計画](#5-テスト計画)
6. [既存コードとの統合](#6-既存コードとの統合)
7. [リスクと対策](#7-リスクと対策)
8. [工数見積もり](#8-工数見積もり)

---

## 1. モジュール設計

### 1.1 目的・責務

**目的**:
`config/mapping.json`に保存されたマッピングデータのCRUD操作（Create, Read, Update, Delete）を提供し、category_logic.pyとFlaskアプリケーションの橋渡しを行う。

**責務**:
- マッピングデータのCRUD操作（追加、読込、更新、削除）
- マッピングデータのバリデーション
- JSONファイルの読み書き・永続化
- ID自動採番管理
- データ整合性の保証（重複チェック、トランザクション風の保存）

**責務外（他モジュールが担当）**:
- パターンマッチング処理（category_logic.pyが担当）
- カテゴリ判定ロジック（category_logic.pyが担当）
- Flask APIエンドポイント（app.pyが担当）

---

### 1.2 パブリックAPI（提供する関数）

| 関数名 | 目的 | 戻り値 |
|-------|-----|--------|
| `get_all_mappings()` | 全マッピングを取得 | `List[MappingEntry]` |
| `get_mapping_by_id(mapping_id: int)` | ID指定でマッピング取得 | `Optional[MappingEntry]` |
| `add_mapping(entry: Dict)` | 新規マッピング追加 | `MappingEntry` |
| `update_mapping(mapping_id: int, entry: Dict)` | マッピング更新 | `MappingEntry` |
| `delete_mapping(mapping_id: int)` | マッピング削除 | `bool` |
| `search_mappings(keyword: str)` | キーワード検索 | `List[MappingEntry]` |
| `get_next_id()` | 次のIDを生成 | `int` |
| `import_mappings(data: Dict)` | JSONデータ一括インポート | `bool` |
| `export_mappings()` | JSONデータエクスポート | `MappingData` |

---

### 1.3 データ構造

**既存型（category_logic.pyから継承）**:
```python
from modules.category_logic import MappingEntry, MappingData
```

**独自型**:
```python
class MappingManagerError(Exception):
    """マッピング管理の基底例外"""
    pass

class MappingNotFoundError(MappingManagerError):
    """マッピングが見つからないエラー"""
    pass

class DuplicateMappingError(MappingManagerError):
    """マッピング重複エラー"""
    pass

class MappingSaveError(MappingManagerError):
    """マッピング保存エラー"""
    pass
```

---

### 1.4 依存関係

**依存モジュール**:
- `modules.category_logic` - 型定義（MappingEntry, MappingData）と検証関数（validate_mapping_entry, validate_mapping_data）を利用
- `json` - JSON読み書き
- `pathlib.Path` - ファイルパス操作
- `typing` - 型ヒント
- `copy.deepcopy` - データコピー（破壊的変更防止）

**被依存モジュール（利用側）**:
- `app.py` - Flask APIエンドポイントから呼び出し
- `modules.category_logic` - load_mapping_dataを使用（読み取り専用）

**依存グラフ**:
```
app.py
  └─> mapping_manager.py
        ├─> category_logic.py (型定義・検証関数)
        └─> config/mapping.json (データファイル)
```

---

## 2. 機能要件

### 2.1 CRUD操作

#### 2.1.1 Create（新規追加）

**関数**: `add_mapping(entry: Dict) -> MappingEntry`

**処理フロー**:
1. 入力データのバリデーション（validate_mapping_entry）
2. 重複チェック（同一patternとmatch_typeの組み合わせ）
3. 次のIDを自動採番（get_next_id）
4. マッピングリストに追加
5. JSONファイル保存
6. 追加したエントリを返却

**バリデーション項目**:
- 必須フィールド: pattern, match_type, category, column, priority
- match_typeの有効値チェック（exact, startswith, contains, keyword）
- columnの有効範囲チェック（B～V）
- priorityの範囲チェック（1～4）

**重複判定基準**:
- `pattern`と`match_type`の組み合わせが同一のエントリは重複とみなす
- 例：`{"pattern": "ユニクロ", "match_type": "contains"}` が既に存在する場合は追加不可

#### 2.1.2 Read（読込）

**関数**: `get_all_mappings() -> List[MappingEntry]`

**処理フロー**:
1. `category_logic.load_mapping_data()`でデータ読込
2. mappingsリストを返却

**関数**: `get_mapping_by_id(mapping_id: int) -> Optional[MappingEntry]`

**処理フロー**:
1. 全マッピング取得
2. IDでフィルタリング
3. 見つからない場合はNone返却

#### 2.1.3 Update（更新）

**関数**: `update_mapping(mapping_id: int, entry: Dict) -> MappingEntry`

**処理フロー**:
1. IDで対象エントリ検索
2. 見つからない場合はMappingNotFoundError
3. 入力データのバリデーション
4. 他エントリとの重複チェック（自身を除く）
5. エントリ更新
6. JSONファイル保存
7. 更新後のエントリ返却

**部分更新対応**:
- 入力Dictに含まれるフィールドのみ更新
- 含まれないフィールドは既存値を維持

#### 2.1.4 Delete（削除）

**関数**: `delete_mapping(mapping_id: int) -> bool`

**処理フロー**:
1. IDで対象エントリ検索
2. 見つからない場合はMappingNotFoundError
3. リストから削除
4. JSONファイル保存
5. 成功時True返却

**安全性**:
- 削除前に確認を促すメッセージをログ出力
- 削除は即座に永続化（ロールバック不可）

---

### 2.2 バリデーション機能

**方針**: `category_logic.py`のバリデーション関数を再利用

- `validate_mapping_entry(entry)` - 単一エントリ検証
- `validate_mapping_data(data)` - データ全体検証

**追加バリデーション**（mapping_manager独自）:
- 重複チェック（pattern + match_typeの組み合わせ）
- ID存在チェック（更新・削除時）

---

### 2.3 ID管理（自動採番）

**関数**: `get_next_id() -> int`

**処理フロー**:
1. 現在の全マッピングを取得
2. 最大IDを取得（リストが空なら0）
3. 最大ID + 1を返却

**採番ルール**:
- IDは1から開始
- 既存の最大ID + 1を次のIDとする
- 削除によりIDが欠番になっても、連番を詰めない（IDの再利用なし）

---

### 2.4 ファイルI/O処理

#### 2.4.1 ファイル読み込み

**方針**: `category_logic.load_mapping_data()`を利用

- UTF-8エンコーディング
- JSONDecodeError時の例外ハンドリング

#### 2.4.2 ファイル書き込み

**関数**: `_save_mapping_data(data: MappingData) -> None`（プライベート関数）

**処理フロー**:
1. データ全体のバリデーション（validate_mapping_data）
2. 一時ファイルに書き込み（`mapping.json.tmp`）
3. 書き込み成功後、本ファイルに置き換え（`os.replace`）
4. エラー時は一時ファイル削除

**アトミック性の確保**:
- 直接`mapping.json`に書き込まず、一時ファイル経由で置き換え
- 書き込み失敗時に元ファイルが破損しないようにする

**JSON整形**:
```python
json.dump(data, f, ensure_ascii=False, indent=2)
```
- `ensure_ascii=False`: 日本語をそのまま出力
- `indent=2`: 可読性向上のためインデント

---

## 3. 実装計画

### フェーズ1: 基本機能（CRUD）

**タスク**:
1. モジュール構造作成（インポート、例外クラス、定数定義）
2. `get_all_mappings()` 実装
3. `get_mapping_by_id()` 実装
4. `get_next_id()` 実装
5. `add_mapping()` 実装
6. `update_mapping()` 実装
7. `delete_mapping()` 実装
8. `_save_mapping_data()` 実装（プライベート）

**完了条件**:
- すべての関数が正常系で動作する
- 基本的なエラーハンドリングが実装されている

---

### フェーズ2: バリデーション・エラーハンドリング

**タスク**:
1. 重複チェック関数（`_check_duplicate_mapping`）実装
2. 各CRUD操作のバリデーション強化
3. カスタム例外クラス整備
4. エラーメッセージの日本語化
5. ログ出力の追加

**完了条件**:
- すべての異常系で適切な例外が発生する
- エラーメッセージが明確でユーザーフレンドリー
- 操作ログが適切に出力される

---

### フェーズ3: テスト作成

**タスク**:
1. `tests/test_mapping_manager.py` 作成
2. CRUD操作の単体テスト
3. バリデーションエラーテスト
4. ファイルI/Oテスト
5. 統合テスト（category_logicとの連携）
6. カバレッジ測定（目標80%以上）

**完了条件**:
- すべてのテストがパスする
- カバレッジ80%以上

---

## 4. 技術仕様

### 4.1 Python標準ライブラリの使用方針

| ライブラリ | 用途 |
|----------|-----|
| `json` | JSONファイル読み書き |
| `pathlib.Path` | ファイルパス操作 |
| `typing` | 型ヒント（List, Dict, Optional） |
| `copy.deepcopy` | データコピー |
| `os` | ファイル操作（os.replace） |
| `logging` | ログ出力 |

---

### 4.2 エラーハンドリング戦略

**原則**:
1. 予測可能なエラーはカスタム例外で明示的に処理
2. 予測不可能なエラーは上位レイヤー（app.py）で処理
3. エラーメッセージは日本語で、原因と対処法を明記

**例外階層**:
```
Exception
  └─ MappingManagerError（基底クラス）
       ├─ MappingNotFoundError（IDが見つからない）
       ├─ DuplicateMappingError（重複）
       └─ MappingSaveError（保存失敗）
```

**エラーメッセージ例**:
```python
raise MappingNotFoundError(
    f"ID {mapping_id} のマッピングが見つかりません。",
    details={'mapping_id': mapping_id}
)
```

---

### 4.3 ログ出力要件

**ログレベル**:
- **INFO**: CRUD操作の開始・成功
- **WARNING**: 重複チェックなどの警告
- **ERROR**: 例外発生時

**ログ出力例**:
```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"マッピング追加: pattern={entry['pattern']}, category={entry['category']}")
logger.error(f"マッピング保存失敗: {str(e)}")
```

---

### 4.4 パフォーマンス考慮事項

**最適化ポイント**:
1. **メモリ効率**: 大量マッピング（1000件以上）でもメモリ使用量を抑える
2. **ファイルI/O**: 書き込み回数を最小化（バッチ更新時も1回のみ）
3. **検索速度**: ID検索はO(n)だが、通常のマッピング件数（100件程度）では問題なし

**性能目標**:
- 100件のマッピングに対する各操作が100ms以内

---

## 5. テスト計画

### 5.1 単体テストの方針

**テストフレームワーク**: `pytest`

**テストファイル**: `tests/test_mapping_manager.py`

**テストカバレッジ目標**: 80%以上（category_logic.pyの89%を参考）

**カバレッジ測定コマンド**:
```bash
# カバレッジ測定（ターミナル出力）
pytest tests/test_mapping_manager.py --cov=modules.mapping_manager --cov-report=term-missing

# カバレッジ測定（HTML レポート生成）
pytest tests/test_mapping_manager.py --cov=modules.mapping_manager --cov-report=html --cov-report=term

# カバレッジレポート確認
# htmlcov/index.html をブラウザで開く
```

**カバレッジ基準**:
- **Statement Coverage（行カバレッジ）**: 80%以上（目標）
- **Branch Coverage（分岐カバレッジ）**: 70%以上（推奨）
- **Function Coverage（関数カバレッジ）**: 100%（すべての関数をテスト）

---

### 5.2 テストケースのカテゴリ

#### 5.2.1 CRUD操作テスト

| テストケース | 説明 |
|-----------|-----|
| `test_get_all_mappings_empty` | 空データでの全件取得 |
| `test_get_all_mappings_normal` | 正常データでの全件取得 |
| `test_get_mapping_by_id_found` | ID検索成功 |
| `test_get_mapping_by_id_not_found` | ID検索失敗 |
| `test_add_mapping_success` | 正常な追加 |
| `test_add_mapping_duplicate` | 重複エラー |
| `test_update_mapping_success` | 正常な更新 |
| `test_update_mapping_not_found` | 更新対象なし |
| `test_delete_mapping_success` | 正常な削除 |
| `test_delete_mapping_not_found` | 削除対象なし |

#### 5.2.2 バリデーションテスト

| テストケース | 説明 |
|-----------|-----|
| `test_validate_invalid_match_type` | 不正なmatch_type |
| `test_validate_invalid_column` | 不正な列番号 |
| `test_validate_missing_required_field` | 必須フィールド不足 |
| `test_validate_invalid_priority` | 不正なpriority |

#### 5.2.3 ファイルI/Oテスト

| テストケース | 説明 |
|-----------|-----|
| `test_save_mapping_data_success` | 正常保存 |
| `test_save_mapping_data_atomic` | アトミック性確認 |
| `test_save_mapping_data_failure` | 保存失敗時の処理 |
| `test_load_mapping_data_integration` | category_logicとの統合 |

#### 5.2.4 ID管理テスト

| テストケース | 説明 |
|-----------|-----|
| `test_get_next_id_empty` | 空データで1を返却 |
| `test_get_next_id_sequential` | 連番生成 |
| `test_get_next_id_after_delete` | 削除後も欠番を埋めない |

#### 5.2.5 検索機能テスト

| テストケース | 説明 |
|-----------|-----|
| `test_search_mappings_by_pattern` | パターンでの検索 |
| `test_search_mappings_by_category` | カテゴリでの検索 |
| `test_search_mappings_no_match` | 検索結果なし |

---

### 5.3 テストデータ準備

**フィクスチャ例**:
```python
import pytest
from pathlib import Path
import json
import tempfile

@pytest.fixture
def temp_mapping_file(tmp_path):
    """一時的なマッピングファイルを作成"""
    mapping_file = tmp_path / "mapping.json"
    data = {
        "version": "1.0",
        "mappings": [
            {
                "id": 1,
                "pattern": "テスト店舗",
                "match_type": "contains",
                "category": "外食費",
                "column": "C",
                "priority": 1
            }
        ],
        "default": {
            "category": "支払額",
            "column": "B"
        }
    }
    with mapping_file.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return mapping_file
```

---

## 6. 既存コードとの統合

### 6.1 category_logic.pyとの連携

**連携ポイント**:
1. **型定義の共有**: `MappingEntry`, `MappingData`をインポート
2. **検証関数の再利用**: `validate_mapping_entry`, `validate_mapping_data`
3. **読込関数の利用**: `load_mapping_data`を内部で使用

**統合例**:
```python
from modules.category_logic import (
    MappingEntry,
    MappingData,
    load_mapping_data,
    validate_mapping_entry,
    validate_mapping_data,
    VALID_MATCH_TYPES,
    VALID_COLUMNS
)
```

---

### 6.2 app.py（Flask）との統合ポイント

**APIエンドポイントとの対応**:

| エンドポイント | 使用関数 |
|-------------|---------|
| `GET /mapping/list` | `get_all_mappings()` |
| `POST /mapping/add` | `add_mapping(request.json)` |
| `PUT /mapping/edit/<id>` | `update_mapping(id, request.json)` |
| `DELETE /mapping/delete/<id>` | `delete_mapping(id)` |

**Flask統合例（エラーハンドリング強化版）**:
```python
from flask import Flask, jsonify, request
from modules import mapping_manager
from modules.mapping_manager import (
    MappingNotFoundError,
    DuplicateMappingError,
    MappingSaveError
)
from modules.category_logic import MappingValidationError
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route('/mapping/list', methods=['GET'])
def list_mappings():
    """マッピング一覧取得"""
    try:
        mappings = mapping_manager.get_all_mappings()
        return jsonify({'status': 'success', 'data': mappings})
    except Exception as e:
        logger.exception("マッピング一覧取得エラー")
        return jsonify({
            'status': 'error',
            'message': '予期しないエラーが発生しました',
            'code': 'INTERNAL_ERROR'
        }), 500

@app.route('/mapping/add', methods=['POST'])
def add_mapping():
    """マッピング追加"""
    try:
        entry = mapping_manager.add_mapping(request.json)
        return jsonify({'status': 'success', 'data': entry}), 201
    except DuplicateMappingError as e:
        return jsonify({
            'status': 'error',
            'message': e.message,
            'code': 'DUPLICATE_MAPPING',
            'details': e.details
        }), 409
    except MappingValidationError as e:
        return jsonify({
            'status': 'error',
            'message': e.message,
            'code': 'VALIDATION_ERROR',
            'details': e.details
        }), 400
    except MappingSaveError as e:
        logger.error(f"マッピング保存エラー: {e}")
        return jsonify({
            'status': 'error',
            'message': e.message,
            'code': 'SAVE_ERROR',
            'details': e.details
        }), 500
    except Exception as e:
        logger.exception("マッピング追加エラー")
        return jsonify({
            'status': 'error',
            'message': '予期しないエラーが発生しました',
            'code': 'INTERNAL_ERROR'
        }), 500

@app.route('/mapping/edit/<int:mapping_id>', methods=['PUT'])
def update_mapping(mapping_id):
    """マッピング更新"""
    try:
        entry = mapping_manager.update_mapping(mapping_id, request.json)
        return jsonify({'status': 'success', 'data': entry})
    except MappingNotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': e.message,
            'code': 'NOT_FOUND',
            'details': e.details
        }), 404
    except DuplicateMappingError as e:
        return jsonify({
            'status': 'error',
            'message': e.message,
            'code': 'DUPLICATE_MAPPING',
            'details': e.details
        }), 409
    except MappingValidationError as e:
        return jsonify({
            'status': 'error',
            'message': e.message,
            'code': 'VALIDATION_ERROR',
            'details': e.details
        }), 400
    except Exception as e:
        logger.exception("マッピング更新エラー")
        return jsonify({
            'status': 'error',
            'message': '予期しないエラーが発生しました',
            'code': 'INTERNAL_ERROR'
        }), 500

@app.route('/mapping/delete/<int:mapping_id>', methods=['DELETE'])
def delete_mapping(mapping_id):
    """マッピング削除"""
    try:
        mapping_manager.delete_mapping(mapping_id)
        return jsonify({'status': 'success', 'message': '削除しました'})
    except MappingNotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': e.message,
            'code': 'NOT_FOUND',
            'details': e.details
        }), 404
    except Exception as e:
        logger.exception("マッピング削除エラー")
        return jsonify({
            'status': 'error',
            'message': '予期しないエラーが発生しました',
            'code': 'INTERNAL_ERROR'
        }), 500
```

**エラーコードとHTTPステータスの対応**:
| 例外クラス | HTTPステータス | エラーコード |
|-----------|---------------|------------|
| `MappingNotFoundError` | 404 Not Found | `NOT_FOUND` |
| `DuplicateMappingError` | 409 Conflict | `DUPLICATE_MAPPING` |
| `MappingValidationError` | 400 Bad Request | `VALIDATION_ERROR` |
| `MappingSaveError` | 500 Internal Server Error | `SAVE_ERROR` |
| その他の例外 | 500 Internal Server Error | `INTERNAL_ERROR` |

---

### 6.3 API互換性の考慮

**下位互換性**:
- category_logic.pyの既存関数（load_mapping_data）は変更しない
- mapping_manager.pyは新規モジュールのため、互換性問題なし

**上位互換性**:
- 将来的にマッピングデータにフィールド追加があっても対応可能な設計
- オプショナルフィールド（note等）をサポート

---

## 7. リスクと対策

### 7.1 想定される課題

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|-----|
| ファイル保存の失敗 | 高 | 低 | アトミックな書き込み、一時ファイル利用 |
| ID重複の発生 | 中 | 低 | get_next_id()で最大値+1を確実に採番 |
| 同時書き込み競合 | 中 | 低 | ファイルロック実装（将来対応） |
| 大量データ時の性能低下 | 低 | 低 | 1000件程度なら問題なし、必要に応じて索引化 |

---

### 7.2 対応方針

**ファイル保存失敗時**:
- 一時ファイル（`.tmp`）経由で書き込み
- os.replace()でアトミックな置き換え
- エラー時は一時ファイルを削除、元ファイルを保護

**バックアップ機能（Phase 2で実装）**:
- 保存前に自動バックアップを作成
- `config/backups/mapping_YYYYMMDD_HHMMSS.json`形式で保存
- 最新10件のバックアップのみ保持（古いものは自動削除）
- 実装例：
  ```python
  from datetime import datetime
  import shutil

  def _create_backup(file_path: Path) -> None:
      """マッピングファイルの自動バックアップ作成"""
      if not file_path.exists():
          return

      # バックアップディレクトリ作成
      backup_dir = file_path.parent / 'backups'
      backup_dir.mkdir(exist_ok=True)

      # タイムスタンプ付きバックアップ
      timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
      backup_file = backup_dir / f"mapping_{timestamp}.json"
      shutil.copy2(file_path, backup_file)

      # 古いバックアップ削除（最新10件保持）
      backups = sorted(backup_dir.glob('mapping_*.json'), reverse=True)
      for old_backup in backups[10:]:
          old_backup.unlink()
          logger.info(f"古いバックアップを削除: {old_backup.name}")

  def _save_mapping_data(data: MappingData) -> None:
      """バックアップ付き保存処理"""
      file_path = Path(DEFAULT_MAPPING_PATH)

      # 保存前にバックアップ作成
      _create_backup(file_path)

      # ファイルロック・一時ファイル経由の保存処理...
  ```

**ID重複防止**:
- get_next_id()で確実に採番
- 追加時にID重複チェック（念のため）

**同時書き込み競合**:
- Phase 1では非対応（単一ユーザー想定）
- **Phase 2でファイルロック実装（必須）**
  - Windows: `msvcrt.locking()`を使用
  - Unix/Linux: `fcntl.flock()`を使用
  - OS判定により適切なロック機構を選択
  - 実装例：
    ```python
    import platform
    import fcntl  # Unix
    import msvcrt  # Windows

    def _save_mapping_data(data: MappingData) -> None:
        file_path = Path(DEFAULT_MAPPING_PATH)
        temp_path = file_path.with_suffix('.json.tmp')

        try:
            with file_path.open('r+', encoding='utf-8') as lock_file:
                # ファイルロック取得
                if platform.system() == 'Windows':
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

                # 一時ファイルに書き込み
                with temp_path.open('w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # アトミックな置き換え
                os.replace(temp_path, file_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise MappingSaveError(f"ファイル保存に失敗: {str(e)}")
    ```

**性能最適化**:
- 通常は100件程度のマッピングのため、最適化不要
- 1000件以上になった場合は索引化を検討

---

## 8. 工数見積もり

### 8.1 フェーズ別見積もり

| フェーズ | タスク | 見積時間 | 備考 |
|---------|-------|---------|-----|
| **フェーズ1** | 基本機能（CRUD） | 4時間 | 8関数実装 |
| **フェーズ2** | バリデーション・セキュリティ強化 | **3時間** | ファイルロック・バックアップ追加 |
| **フェーズ3** | テスト作成 | 4時間 | 30+テストケース作成 |
| **統合・調整** | app.py統合、ドキュメント更新 | 2時間 | Flask統合、README更新 |
| **合計** | - | **13時間** | 約1.5日 |

---

### 8.2 各フェーズの詳細タスク

#### フェーズ1: 基本機能（4時間）
- [ ] モジュール構造作成（30分）
- [ ] get_all_mappings() 実装（30分）
- [ ] get_mapping_by_id() 実装（30分）
- [ ] get_next_id() 実装（30分）
- [ ] add_mapping() 実装（1時間）
- [ ] update_mapping() 実装（1時間）
- [ ] delete_mapping() 実装（30分）

#### フェーズ2: バリデーション・セキュリティ強化（3時間）
- [ ] 重複チェック関数実装（1時間）
- [ ] **ファイルロック実装（30分）** - 同時書き込み対策
- [ ] **バックアップ機能実装（30分）** - データ損失防止
- [ ] エラーハンドリング強化（30分）
- [ ] ログ出力追加（30分）

#### フェーズ3: テスト作成（4時間）
- [ ] テストファイル作成・フィクスチャ準備（1時間）
- [ ] CRUD操作テスト（1.5時間）
- [ ] バリデーション・エラーテスト（1時間）
- [ ] カバレッジ測定・改善（30分）

#### 統合・調整（2時間）
- [ ] app.py統合（1時間）
- [ ] ドキュメント更新（30分）
- [ ] 最終動作確認（30分）

---

## 9. 実装チェックリスト

### 9.1 コード品質

- [ ] PEP 8準拠（100%）
- [ ] すべての関数にdocstring（日本語または英語）
- [ ] すべての関数に型ヒント
- [ ] エラーメッセージが明確（日本語）
- [ ] ログ出力が適切

### 9.2 機能要件

- [ ] CRUD操作がすべて正常動作
- [ ] バリデーションが適切に動作
- [ ] ID自動採番が正しく動作
- [ ] ファイル保存がアトミック
- [ ] category_logic.pyと連携

### 9.3 テスト

- [ ] 単体テストが80%以上のカバレッジ
- [ ] すべてのテストがパス
- [ ] 異常系テストが充実

### 9.4 統合

- [ ] app.pyとの統合動作確認
- [ ] category_logic.pyとの連携確認
- [ ] ドキュメント更新完了

---

## 10. 参考資料

### 10.1 関連ドキュメント

- `.claude/00_project/08_dev_step.md` - Step 2.3の概要
- `.claude/02_backend/02_backend_modules_spec.md` - モジュール仕様
- `.claude/02_backend/03_mapping_table_definition.md` - マッピングテーブル定義
- `.claude/01_development_docs/00_system_architecture.md` - システムアーキテクチャ
- `modules/category_logic.py` - 関連モジュール（既存）
- `config/mapping.json` - マッピングデータ構造

### 10.2 既存コード参考

- `modules/category_logic.py` - 型定義、検証関数、エラーハンドリングのパターン
- `tests/test_category_logic.py` - テストコードのパターン（存在する場合）

---

## 11. 次のステップ

1. **実装フェーズ**: この計画書をもとに`modules/mapping_manager.py`を実装
2. **テストフェーズ**: `tests/test_mapping_manager.py`を作成し、テスト実行
3. **統合フェーズ**: `app.py`に統合し、E2Eテスト実行
4. **ドキュメント更新**: README.md、CLAUDE.mdを更新

---

**作成者**: Claude Code (backend-code-generator)
**レビュー**: 完了（project-orchestrator）
**レビュー結果**: A+（プロダクション品質）
**改善反映**: 完了（2025-12-16）
**承認**: 承認推奨

---

## 改訂履歴

| 版 | 日付 | 変更内容 | 担当 |
|----|------|---------|------|
| 1.0 | 2025-12-16 | 初版作成 | backend-code-generator |
| 1.1 | 2025-12-16 | レビュー指摘事項反映 | backend-code-generator |

**主な改善内容（v1.1）**:
1. Phase 2に「ファイルロック実装」を追加（30分）
2. Phase 2に「バックアップ機能実装」を追加（30分）
3. Phase 2の工数を2時間→3時間に調整
4. 合計工数を12時間→13時間に調整
5. ファイルロック実装の詳細コード例を追加
6. バックアップ機能の詳細コード例を追加
7. Flask統合時のエラーハンドリングを強化（全4エンドポイント）
8. カバレッジ測定コマンドと基準を明記
