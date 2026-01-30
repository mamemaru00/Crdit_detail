# SQLiteセッションストア実装 - エージェント割り振り指示書

**作成日**: 2025-12-30
**関連ドキュメント**: `09_session_store_implementation_plan.md`
**プロジェクト**: イオンカード明細取込システム
**フェーズ**: Phase 3 Session Management Enhancement

---

## エージェント割り振りサマリー

| エージェント | 担当フェーズ | 主要タスク | 想定時間 |
|------------|------------|-----------|---------|
| **backend-code-generator** | Phase 1-5 | コード実装、テスト、ドキュメント作成 | 7.5時間 |
| **security-compliance-auditor** | Phase 3 | セキュリティレビュー（オプション） | 0.5時間 |
| **project-compliance-tester** | Phase 4 | E2Eテスト、パフォーマンステスト（オプション） | 1時間 |

---

## backend-code-generator への指示

### 概要

**役割**: SQLiteセッションストアの実装を担当する主要エージェント

**目的**: Cookie 4KB制限を解決し、セッションデータをサーバーサイドで安全に管理する

**参照ドキュメント**:
- `C:\work\Lesson\個人開発\Crdit_detail\.claude\02_backend\09_session_store_implementation_plan.md`（必読）
- `C:\work\Lesson\個人開発\Crdit_detail\CLAUDE.md`（プロジェクト全体ガイド）
- `C:\work\Lesson\個人開発\Crdit_detail\.claude\02_backend\00_backend_architecture.md`（バックエンドアーキテクチャ）

---

### Phase 1: 基盤実装（想定時間: 2時間）

#### タスク1.1: `modules/session_store.py` 実装

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\modules\session_store.py`

**実装要件**:

1. **モジュールヘッダー**:
```python
"""
SQLiteベースのセッションストアモジュール

このモジュールは、Flaskセッションデータをサーバーサイドで管理するための
SQLiteストレージを提供します。

主な機能:
- セッションデータのCRUD操作
- 有効期限管理（TTL）
- 自動クリーンアップ
- WALモード対応

Author: Claude Code
Created: 2025-12-30
Version: 1.0
"""
```

2. **インポート**:
```python
import sqlite3
import json
import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path
from contextlib import contextmanager
```

3. **例外クラス**:
```python
class SessionStoreError(Exception):
    """SessionStore基底例外クラス"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
```

4. **SessionStoreクラス実装**:

**必須メソッド**:
- `__init__(self, db_path: str, ttl_seconds: int = 1800)`
- `_init_db(self) -> None`
- `_get_connection(self)` （コンテキストマネージャー）
- `save(self, session_id: str, data: dict) -> bool`
- `load(self, session_id: str) -> Optional[dict]`
- `delete(self, session_id: str) -> bool`
- `prune_expired(self) -> int`
- `wal_checkpoint(self) -> bool`

**実装詳細は計画書「4. モジュール設計」を参照**。

5. **SQLiteスキーマ**:
```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at);
```

6. **WALモード設定**:
```python
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA wal_autocheckpoint=1000;
PRAGMA busy_timeout=5000;
```

**重要事項**:
- すべてのSQLite操作は`try-except`でエラーハンドリング
- エラーは`SessionStoreError`でラップして再送出
- すべての操作をロギング（`logger.info`, `logger.error`）
- JSON変換エラーも適切にハンドリング
- 有効期限切れセッションは`load()`時に自動削除

**成果物**:
- [ ] `modules/session_store.py` 完成版
- [ ] SQLiteスキーマ定義実装確認
- [ ] WALモード有効化確認

---

### Phase 2: app.py統合（想定時間: 1.5時間）

#### タスク2.1: `app.py` セッション書き込み箇所修正

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\app.py`

**修正箇所1（363行付近）**:
```python
# 現在のコード
session['csv_data'] = result['details']

# 修正後のコード
session_data = session_store.load(session.sid) or {}
session_data['csv_data'] = result['details']
session_store.save(session.sid, session_data)
```

**修正箇所2（559行付近）**:
```python
# 現在のコード
session['process_result'] = result_data

# 修正後のコード
session_data = session_store.load(session.sid) or {}
session_data['process_result'] = result_data
session_store.save(session.sid, session_data)
```

**修正箇所3（276行付近）**:
```python
# 現在のコード
session['uploaded_file_path'] = file_path
session['uploaded_filename'] = filename

# 修正後のコード
session_data = session_store.load(session.sid) or {}
session_data['uploaded_file_path'] = file_path
session_data['uploaded_filename'] = filename
session_store.save(session.sid, session_data)
```

**注意事項**:
- セッションIDは`session.sid`で取得
- `session_store.load()`がNoneを返す場合は空辞書`{}`を使用
- エラーハンドリングを追加（`SessionStoreError`をキャッチ）

---

#### タスク2.2: `app.py` セッション読み込み箇所修正

**修正箇所1（333行付近）**:
```python
# 現在のコード
file_path = session.get('uploaded_file_path')

# 修正後のコード
session_data = session_store.load(session.sid) or {}
file_path = session_data.get('uploaded_file_path')
```

**修正箇所2（456行付近）**:
```python
# 現在のコード
csv_data = session.get('csv_data')

# 修正後のコード
session_data = session_store.load(session.sid) or {}
csv_data = session_data.get('csv_data')
```

**修正箇所3（200行付近）**:
```python
# 現在のコード
result_data = session.get('process_result')

# 修正後のコード
session_data = session_store.load(session.sid) or {}
result_data = session_data.get('process_result')
```

---

#### タスク2.3: `app.py` 初期化処理追加

**追加箇所（47行付近、アップロードフォルダ作成の後）**:
```python
# アップロードフォルダの作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 必要なディレクトリを自動作成
os.makedirs(Path(app.config['LOG_FILE']).parent, exist_ok=True)
os.makedirs('data/backups', exist_ok=True)

# === 追加: SessionStore初期化 ===
from modules.session_store import SessionStore

# セッションディレクトリ作成
os.makedirs(Path(app.config['SESSION_DB_PATH']).parent, exist_ok=True)

# SessionStoreインスタンス生成
session_store = SessionStore(
    db_path=app.config['SESSION_DB_PATH'],
    ttl_seconds=app.config['SESSION_TTL_SECONDS']
)

logger.info(f"SessionStore初期化完了: {app.config['SESSION_DB_PATH']}")
```

---

#### タスク2.4: `app.py` クリーンアップ処理追加

**追加箇所1（1107行付近、アプリケーション起動前）**:
```python
if __name__ == '__main__':
    logger.info("アプリケーションを起動します")
    logger.info(f"環境: {env}")
    logger.info(f"デバッグモード: {app.config['DEBUG']}")
    logger.info(f"アップロードフォルダ: {app.config['UPLOAD_FOLDER']}")

    # === 追加: 古いセッションのクリーンアップ ===
    try:
        deleted_count = session_store.prune_expired()
        logger.info(f"古いセッションを削除: {deleted_count}件")
    except Exception as e:
        logger.warning(f"セッションクリーンアップ中にエラー: {str(e)}")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )
```

**追加箇所2（283行付近、uploadエンドポイント内）**:
```python
# 8. 古いファイルのクリーンアップ（非同期的に実行）
cleanup_old_files(app.config['UPLOAD_FOLDER'])

# === 追加: 古いセッションのクリーンアップ ===
try:
    session_store.prune_expired()
except Exception as e:
    logger.warning(f"セッションクリーンアップ中にエラー: {str(e)}")

return jsonify(create_response(
    'success',
    # ... 以下既存コード ...
))
```

---

#### タスク2.5: `app.py` セッション削除処理修正

**修正箇所（963行付近、clear_sessionエンドポイント）**:
```python
@app.route('/clear_session', methods=['POST'])
@csrf.exempt
def clear_session():
    """セッションをクリアする"""
    logger.info("セッションクリア処理を開始")

    try:
        # === 修正: セッションストアからファイルパス取得 ===
        session_data = session_store.load(session.sid) or {}
        file_path = session_data.get('uploaded_file_path')

        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"アップロードファイルを削除: {file_path}")

        # === 追加: セッションストアからデータ削除 ===
        session_store.delete(session.sid)

        # Cookieセッションもクリア
        session.clear()

        logger.info("セッションクリア完了")

        return jsonify(create_response(
            'success',
            message='セッションをクリアしました'
        ))

    except Exception as e:
        logger.error(f"セッションクリア中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'セッションのクリアに失敗しました: {str(e)}'
        )), 500
```

---

#### タスク2.6: `config.py` セッションストア設定追加

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\config.py`

**追加箇所（Configクラス内、26行付近のCSV_ENCODINGの後）**:
```python
# アプリケーション設定
DEFAULT_YEAR = int(os.environ.get('DEFAULT_YEAR', '2025'))
DEFAULT_COLUMN = 'B'
CSV_ENCODING = 'Shift_JIS'

# === 追加: セッションストア設定 ===
# セッションDB設定
SESSION_DB_PATH = os.path.join('session', 'sessions.db')
SESSION_TTL_SECONDS = int(os.environ.get('SESSION_TTL_SECONDS', '1800'))  # 30分
SESSION_CLEANUP_INTERVAL_HOURS = int(os.environ.get('SESSION_CLEANUP_INTERVAL_HOURS', '6'))  # 6時間

# API 設定
API_TIMEOUT = 30
BATCH_SIZE = 100
```

**成果物**:
- [ ] `app.py` 修正版（全6箇所修正完了）
- [ ] `config.py` 修正版

---

### Phase 3: Docker統合（想定時間: 1時間）

#### タスク3.1: `docker-compose.yml` 修正

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\docker-compose.yml`

**修正箇所（volumes設定）**:
```yaml
volumes:
  # 認証情報（読み取り専用）
  - ./config:/app/config:ro
  # アプリケーションデータ（読み書き可能）
  - ./data:/app/data
  # アップロードファイル（読み書き可能）
  - ./uploads:/app/uploads
  # ログファイル（読み書き可能）
  - ./logs:/app/logs
  # === 追加: セッションDBファイル ===
  - ./session:/app/session
```

**オプション: 環境変数追加**:
```yaml
environment:
  # Flask環境設定
  - FLASK_ENV=production
  - SECRET_KEY=${SECRET_KEY:-default-secret-key-change-in-production}

  # Google Sheets設定
  - SPREADSHEET_ID=${SPREADSHEET_ID:-}

  # アプリケーション設定
  - DEFAULT_YEAR=${DEFAULT_YEAR:-2025}
  - LOG_LEVEL=${LOG_LEVEL:-INFO}

  # === 追加: セッションストア設定 ===
  - SESSION_TTL_SECONDS=${SESSION_TTL_SECONDS:-1800}
  - SESSION_CLEANUP_INTERVAL_HOURS=${SESSION_CLEANUP_INTERVAL_HOURS:-6}

  # Pythonバッファリング無効化（ログ即時出力）
  - PYTHONUNBUFFERED=1
```

---

#### タスク3.2: `Dockerfile` 修正

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\Dockerfile`

**修正箇所（29行）**:
```dockerfile
# 必要ディレクトリ作成
RUN mkdir -p uploads logs config session
```

---

#### タスク3.3: `.gitignore` 修正

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\.gitignore`

**追加内容（ファイル末尾）**:
```gitignore
# Session Store
session/*.db
session/*.db-shm
session/*.db-wal
```

**成果物**:
- [ ] `docker-compose.yml` 修正版
- [ ] `Dockerfile` 修正版
- [ ] `.gitignore` 修正版

---

### Phase 4: テスト（想定時間: 2時間）

#### タスク4.1: 単体テスト実装

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\tests\test_session_store.py`（新規作成）

**テスト構成**:
```python
"""
SessionStore単体テスト

テストケース:
- 初期化テスト（3ケース）
- 保存テスト（4ケース）
- 読み込みテスト（4ケース）
- 削除テスト（2ケース）
- 有効期限管理テスト（3ケース）
- WAL管理テスト（2ケース）
- エラーハンドリングテスト（3ケース）

Author: Claude Code
Created: 2025-12-30
"""

import pytest
import sqlite3
import json
import time
from pathlib import Path
from modules.session_store import SessionStore, SessionStoreError
```

**実装必須テストケース**（計21ケース）:

1. **初期化テスト**:
   - `test_init_creates_db_file`: DBファイル作成確認
   - `test_init_creates_table`: テーブル作成確認
   - `test_init_enables_wal_mode`: WALモード有効化確認

2. **保存テスト**:
   - `test_save_new_session`: 新規セッション保存
   - `test_save_update_session`: 既存セッション更新
   - `test_save_large_data`: 大容量データ（100KB）保存
   - `test_save_special_characters`: 特殊文字を含むデータ保存

3. **読み込みテスト**:
   - `test_load_existing_session`: 既存セッション読み込み
   - `test_load_nonexistent_session`: 存在しないセッションはNone
   - `test_load_expired_session`: 有効期限切れセッション自動削除
   - `test_load_large_data`: 大容量データ読み込み

4. **削除テスト**:
   - `test_delete_existing_session`: 既存セッション削除
   - `test_delete_nonexistent_session`: 存在しないセッション削除（エラーなし）

5. **有効期限管理テスト**:
   - `test_prune_expired_sessions`: 有効期限切れセッション削除
   - `test_prune_no_expired_sessions`: 有効セッション保持
   - `test_ttl_setting`: TTL設定反映確認

6. **WAL管理テスト**:
   - `test_wal_checkpoint`: WALチェックポイント成功
   - `test_wal_file_cleanup`: WALファイルクリーンアップ

7. **エラーハンドリングテスト**:
   - `test_invalid_json_data`: JSON化不可データでエラー
   - `test_db_lock_handling`: DBロック時エラーハンドリング
   - `test_corrupted_db_handling`: DB破損時エラーハンドリング

**テスト実装ガイドライン**:
- `pytest`フレームワーク使用
- `@pytest.fixture`でテスト用DBファイル作成・削除
- テストごとに独立したDBファイルを使用
- `assert`文で検証
- エラーテストは`pytest.raises(SessionStoreError)`を使用

---

#### タスク4.2: 統合テスト実装

**テストケース**:

1. **CSVアップロードフロー**:
   - `test_upload_and_preview_flow`: アップロード → プレビュー → セッション保存
   - `test_upload_preserves_session`: セッションデータ保持確認

2. **CSV処理フロー**:
   - `test_process_flow`: プレビュー → 処理 → 結果保存 → 結果表示
   - `test_process_1000_records`: 1000件CSV処理時のセッション保存

3. **セッションクリア**:
   - `test_clear_session_removes_data`: セッションクリアでデータ削除

**実装方法**:
- Flaskテストクライアント（`app.test_client()`）を使用
- セッションストアのデータを直接確認
- CSVファイルはフィクスチャで用意

---

#### タスク4.3: E2Eテスト・パフォーマンステスト

**E2Eテストシナリオ**:
1. 通常フロー（1000件CSV）
2. 複数ワーカーテスト（Gunicorn 4ワーカー）
3. WAL肥大化テスト（100回保存/削除）
4. TTL有効期限テスト（30分経過後）

**パフォーマンステスト**:
1. 保存性能: 1000件CSV（約100KB）を100ms以内で保存
2. 読み込み性能: 1000件CSVを50ms以内で読み込み
3. クリーンアップ性能: 1000セッションを1秒以内で削除
4. 同時アクセス: 4ワーカー × 10ユーザーでエラーなし

**実装方法**:
- `time`モジュールで処理時間測定
- `threading`で同時アクセスシミュレート
- テスト結果をログ出力

**成果物**:
- [ ] `tests/test_session_store.py` 完成版（全21テストケース実装）
- [ ] 統合テスト実装
- [ ] E2Eテスト実施レポート
- [ ] パフォーマンステスト実施レポート

---

### Phase 5: ドキュメント（想定時間: 1時間）

#### タスク5.1: CLAUDE.md更新

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\CLAUDE.md`

**更新箇所1（Technology Stack - Backend）**:
```markdown
### Backend
- **Python**: 3.10+ (Docker: 3.12-slim-bookworm, LTS 2028年まで)
- **Flask**: 3.0+ (推奨 3.1.2)
- **pandas**: 2.0+ (CSV処理・データ操作)
- **google-api-python-client**: 2.100+ (Google Sheets API連携)
- **google-auth**: 2.23+ (OAuth認証)
- **gspread**: 6.x (Google Sheets連携)
- **chardet**: 文字コード検出
- **SQLite**: 3.x (セッションストア) ← 追加
```

**更新箇所2（Directory Structure）**:
```markdown
project_root/
├── app.py                 # メインアプリケーション
├── config.py              # 設定ファイル
├── requirements.txt       # 依存パッケージ
├── Dockerfile
├── docker-compose.yml
├── .env                   # 環境変数（.gitignore対象）
├── .env.example           # 環境変数テンプレート
├── config/
│   └── service_account.json  # Google認証情報（.gitignore対象）
├── data/
│   ├── mapping.json          # カテゴリマッピング
│   └── backups/              # マッピングバックアップ（.gitignore対象）
├── session/                  # セッションストア（.gitignore対象） ← 追加
│   └── sessions.db           # SQLiteセッションDB（.gitignore対象） ← 追加
├── static/                   # フロントエンド静的ファイル
...（以下既存）
```

**更新箇所3（Key Features）**:
```markdown
## Key Features

1. **CSVファイル取込**
   - Shift_JISエンコーディングの利用明細CSVをアップロード・解析
   - 6桁日付（YYMMDD）→ YYYY/MM/DD 変換
   - 明細データ抽出

2. **カテゴリ自動判定**
   - 店舗名から食材費、外食費、雑貨費などのカテゴリを自動振り分け
   - パターンマッチング（完全一致、前方一致、部分一致）
   - 優先順位の適用

3. **スプレッドシート自動更新**
   - Googleスプレッドシートの該当する年・月・カテゴリに金額を自動加算
   - 年別シート選択（2025年、2024年など）
   - 月別行（1月～12月）・カテゴリ別列（B～V列）への書き込み

4. **マッピング管理**
   - 店舗名とカテゴリの対応関係を管理・編集
   - CRUD操作（登録、更新、削除）
   - JSON形式でデータ永続化

5. **未登録店舗管理**
   - マッピング未登録店舗の自動検知
   - 金額合計と処理件数の表示
   - 新規マッピング登録機能

6. **セッション管理** ← 追加
   - SQLiteベースのサーバーサイドセッションストア
   - Cookie 4KB制限の解消
   - セッションデータのセキュア管理
   - 自動有効期限管理（TTL: 30分）
```

---

#### タスク5.2: セッションストア仕様書作成

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\.claude\02_backend\10_session_store_specification.md`

**内容**:
1. セッションストア概要
2. SQLiteスキーマ定義
3. SessionStoreクラス仕様
   - 全メソッドのAPI仕様
   - エラーハンドリング仕様
   - WALモード設定詳細
4. TTL（有効期限）管理仕様
5. パフォーマンス特性
6. セキュリティ考慮事項
7. 運用ガイドライン

**参照**:
- 実装計画書の「3. データベース設計」
- 実装計画書の「4. モジュール設計」
- 実装計画書の「11. リスク管理計画」

---

#### タスク5.3: 実装完了レポート作成

**ファイルパス**: `C:\work\Lesson\個人開発\Crdit_detail\.claude\02_backend\11_session_store_implementation_report.md`

**内容**:
1. **実装サマリー**
   - 実装日時
   - 実装者
   - 実装内容概要

2. **実装詳細**
   - 新規ファイル一覧
   - 修正ファイル一覧
   - 修正箇所サマリー

3. **テスト結果**
   - 単体テスト結果（21ケース）
   - 統合テスト結果
   - E2Eテスト結果
   - パフォーマンステスト結果

4. **性能測定結果**
   - 保存性能（1000件CSV）
   - 読み込み性能（1000件CSV）
   - クリーンアップ性能
   - 同時アクセステスト結果

5. **課題・今後の改善点**
   - 検出された課題
   - 改善提案

6. **結論**
   - Cookie 4KB制限解決確認
   - パフォーマンス目標達成確認
   - セキュリティ要件充足確認

**成果物**:
- [ ] CLAUDE.md更新版
- [ ] `.claude/02_backend/10_session_store_specification.md`
- [ ] `.claude/02_backend/11_session_store_implementation_report.md`

---

## 重要な実装注意事項

### 1. セッションID取得方法

**正しい方法**:
```python
session_id = session.sid
```

**注意**: `session.sid`はFlask 2.0以降で利用可能。Flask 1.x系では`session.get('_id')`等を使用。

### 2. エラーハンドリング

すべてのセッションストア操作は`try-except`でエラーハンドリング:
```python
try:
    session_data = session_store.load(session.sid) or {}
    csv_data = session_data.get('csv_data')
except SessionStoreError as e:
    logger.error(f"セッションストアエラー: {e.message}")
    # 代替処理（Cookieセッションにフォールバック等）
```

### 3. 大容量データのJSON化

1000件CSVデータは約100KBになる可能性があるため、JSON変換を慎重に:
```python
# 大容量データの保存
data_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
```

### 4. WALモード動作確認

WALモードが有効化されているか確認:
```python
cursor.execute("PRAGMA journal_mode")
result = cursor.fetchone()
assert result[0] == 'wal', "WALモードが有効化されていません"
```

### 5. セッションストア初期化タイミング

**SessionStoreインスタンスはapp.py起動時に1回のみ生成**。各リクエストで再生成しない。

### 6. テスト実施順序

1. 単体テスト → 2. 統合テスト → 3. E2Eテスト → 4. パフォーマンステスト

単体テストが通過しない限り、次のテストに進まない。

---

## 成果物チェックリスト

実装完了時、以下をすべてチェック:

### Phase 1
- [ ] `modules/session_store.py` 実装完了
- [ ] SQLiteスキーマ初期化確認
- [ ] WALモード有効化確認

### Phase 2
- [ ] `app.py` セッション書き込み箇所修正（3箇所）
- [ ] `app.py` セッション読み込み箇所修正（3箇所）
- [ ] `app.py` 初期化処理追加
- [ ] `app.py` クリーンアップ処理追加
- [ ] `app.py` セッション削除処理修正
- [ ] `config.py` セッションストア設定追加

### Phase 3
- [ ] `docker-compose.yml` セッションDBボリューム追加
- [ ] `Dockerfile` セッションディレクトリ作成追加
- [ ] `.gitignore` セッションDBファイル除外追加

### Phase 4
- [ ] `tests/test_session_store.py` 全21テストケース実装
- [ ] 統合テスト実装
- [ ] E2Eテスト実施
- [ ] パフォーマンステスト実施

### Phase 5
- [ ] CLAUDE.md更新
- [ ] `.claude/02_backend/10_session_store_specification.md` 作成
- [ ] `.claude/02_backend/11_session_store_implementation_report.md` 作成

### 最終確認
- [ ] Dockerコンテナビルド成功
- [ ] Dockerコンテナ起動成功
- [ ] CSVアップロード → プレビュー → 処理フロー動作確認
- [ ] 1000件CSV処理成功（30秒以内）
- [ ] 全テストパス
- [ ] パフォーマンス目標達成

---

## 質疑応答・サポート

実装中に不明点がある場合:

1. **実装計画書を参照**: `09_session_store_implementation_plan.md`
2. **CLAUDE.mdを参照**: プロジェクト全体ガイド
3. **バックエンドアーキテクチャを参照**: `.claude/02_backend/00_backend_architecture.md`
4. **プロジェクトオーケストレーターに質問**: 実装計画書で不明な箇所を明確化

---

**実装開始時刻**: 2025-12-30（ユーザー承認後）
**実装完了予定**: 2025-12-30（7.5時間後）

**担当者**: backend-code-generator
**レビュアー**: security-compliance-auditor（オプション）
**テスター**: project-compliance-tester（オプション）

---

**END OF DOCUMENT**
