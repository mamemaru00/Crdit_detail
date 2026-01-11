# SQLiteセッションストア実装計画

**作成日**: 2025-12-30
**対象システム**: イオンカード明細取込システム
**対象フェーズ**: Phase 3 Session Management Enhancement
**目的**: Cookie 4KB制限の解決とセッションデータの安全な管理

---

## 1. 実装概要

### 1.1 背景と課題

**現状の問題（Critical）**:
- **Cookie 4KB制限**: 1000件のCSVデータ（約100KB）をCookieセッションに保存すると制限を超過
- **クライアント露出**: セッションデータがCookieに保存されるため、ブラウザに露出
- **パフォーマンス低下**: 大量データをCookieで送受信するとネットワークオーバーヘッドが発生

**app.pyでのセッション書き込み箇所**:
- `363行`: `session['csv_data'] = result['details']` - CSVプレビュー後の全データ保存
- `559行`: `session['process_result'] = result_data` - 処理結果サマリー保存
- `276行`: `session['uploaded_file_path'] = file_path` - アップロードファイルパス保存

### 1.2 解決策

**SQLiteベースのサーバーサイドセッションストア**を実装し、以下を実現：

1. **サーバーサイド保存**: セッションデータをSQLiteに保存し、CookieにはセッションIDのみ保存
2. **容量制限解消**: SQLiteにより実質的に無制限のセッションデータを保存可能
3. **セキュリティ強化**: セッションデータがクライアントに露出しない
4. **パフォーマンス改善**: Cookieサイズ削減によりネットワークオーバーヘッドを軽減

### 1.3 技術選定理由

**SQLiteを選択した理由**:
- **ローカル環境**: 本システムはDocker Desktop上のローカル環境で動作（外部DB不要）
- **ゼロ設定**: SQLiteは追加インフラ不要でファイルベースで動作
- **Python標準ライブラリ**: `sqlite3`モジュールが標準搭載（依存関係追加不要）
- **信頼性**: ACID準拠、WALモードによる同時実行制御
- **軽量**: メモリフットプリントが小さく、ローカル環境に最適

**代替案との比較**:
- Redis: 外部サーバー必要、ローカル環境には過剰
- PostgreSQL: 外部DB必要、ローカル環境には過剰
- ファイルベース（pickle）: ロック制御が複雑、同時実行に弱い

---

## 2. 実装スコープ

### 2.1 新規ファイル

#### `modules/session_store.py`
SQLiteセッションストアの実装モジュール。

**主要機能**:
- セッション保存（save）
- セッション読み込み（load）
- セッション削除（delete）
- 有効期限管理（prune_expired）
- WALチェックポイント（wal_checkpoint）

**クラス構造**:
```python
class SessionStore:
    def __init__(self, db_path: str, ttl_seconds: int = 1800)
    def save(self, session_id: str, data: dict) -> bool
    def load(self, session_id: str) -> Optional[dict]
    def delete(self, session_id: str) -> bool
    def prune_expired(self) -> int
    def wal_checkpoint(self) -> bool
```

### 2.2 修正ファイル

#### `app.py`
- セッション書き込み箇所の置き換え（3箇所）
- セッション読み込み箇所の置き換え（3箇所）
- SessionStoreインスタンス初期化
- 古いセッションのクリーンアップ処理追加

#### `config.py`
- セッションストア設定追加
  - `SESSION_DB_PATH`: SQLiteファイルパス
  - `SESSION_TTL_SECONDS`: セッション有効期限（秒）
  - `SESSION_CLEANUP_INTERVAL`: クリーンアップ間隔（時間）

#### `docker-compose.yml`
- セッションDBファイル用ボリューム追加
  - `./session:/app/session` ボリュームマウント

#### `Dockerfile`
- セッションディレクトリ作成
  - `RUN mkdir -p session`

#### `.gitignore`
- セッションDBファイルを除外
  - `session/*.db`
  - `session/*.db-shm`
  - `session/*.db-wal`

### 2.3 テストファイル

#### `tests/test_session_store.py`（新規）
- 単体テスト
- 統合テスト
- パフォーマンステスト

---

## 3. データベース設計

### 3.1 SQLiteスキーマ

```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,      -- セッションID（UUID v4）
    data TEXT NOT NULL,               -- セッションデータ（JSON形式）
    created_at INTEGER NOT NULL,      -- 作成日時（UNIX timestamp）
    updated_at INTEGER NOT NULL,      -- 更新日時（UNIX timestamp）
    expires_at INTEGER NOT NULL       -- 有効期限（UNIX timestamp）
);

-- 有効期限インデックス（期限切れセッション削除の高速化）
CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at);
```

### 3.2 データ型定義

| カラム名 | データ型 | NULL | 説明 | 例 |
|---------|---------|------|------|---|
| session_id | TEXT | NOT NULL | セッションID | `3e7a8f9b-1c2d-4e5f-6a7b-8c9d0e1f2a3b` |
| data | TEXT | NOT NULL | JSON形式のセッションデータ | `{"csv_data": [...], "uploaded_file_path": "..."}` |
| created_at | INTEGER | NOT NULL | 作成日時（UNIX timestamp） | `1735564800` |
| updated_at | INTEGER | NOT NULL | 更新日時（UNIX timestamp） | `1735566600` |
| expires_at | INTEGER | NOT NULL | 有効期限（UNIX timestamp） | `1735568400` |

### 3.3 インデックス設計

- **PRIMARY KEY**: `session_id` - セッション検索の高速化
- **INDEX**: `idx_expires_at` - 有効期限切れセッション削除の高速化

### 3.4 WALモード設定

```python
# WAL（Write-Ahead Logging）モード有効化
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA wal_autocheckpoint=1000;
```

**WALモードの利点**:
- **同時実行性向上**: 読み取りと書き込みがブロックしない
- **パフォーマンス向上**: 書き込み処理が高速化
- **データ整合性**: クラッシュ時のデータ保護

**WALファイル管理**:
- `session/sessions.db`: メインDBファイル
- `session/sessions.db-wal`: WALログファイル
- `session/sessions.db-shm`: 共有メモリファイル

---

## 4. モジュール設計

### 4.1 `modules/session_store.py` 設計

#### 4.1.1 クラス構造

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

import sqlite3
import json
import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path
from contextlib import contextmanager


class SessionStoreError(Exception):
    """SessionStore基底例外クラス"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class SessionStore:
    """
    SQLiteベースのセッションストアクラス

    Attributes:
        db_path (str): SQLiteデータベースファイルパス
        ttl_seconds (int): セッション有効期限（秒）
        logger (logging.Logger): ロガー
    """

    def __init__(self, db_path: str, ttl_seconds: int = 1800):
        """
        SessionStoreインスタンスを初期化

        Args:
            db_path (str): SQLiteファイルパス
            ttl_seconds (int): セッション有効期限（秒、デフォルト30分）
        """
        pass

    def _init_db(self) -> None:
        """データベーステーブル初期化とWALモード設定"""
        pass

    @contextmanager
    def _get_connection(self):
        """データベース接続コンテキストマネージャー"""
        pass

    def save(self, session_id: str, data: dict) -> bool:
        """
        セッションデータを保存

        Args:
            session_id (str): セッションID
            data (dict): セッションデータ（JSON化可能な辞書）

        Returns:
            bool: 保存成功時True

        Raises:
            SessionStoreError: 保存処理失敗時
        """
        pass

    def load(self, session_id: str) -> Optional[dict]:
        """
        セッションデータを読み込み

        Args:
            session_id (str): セッションID

        Returns:
            Optional[dict]: セッションデータ、存在しない場合None

        Raises:
            SessionStoreError: 読み込み処理失敗時
        """
        pass

    def delete(self, session_id: str) -> bool:
        """
        セッションを削除

        Args:
            session_id (str): セッションID

        Returns:
            bool: 削除成功時True

        Raises:
            SessionStoreError: 削除処理失敗時
        """
        pass

    def prune_expired(self) -> int:
        """
        有効期限切れセッションを削除

        Returns:
            int: 削除されたセッション数

        Raises:
            SessionStoreError: クリーンアップ処理失敗時
        """
        pass

    def wal_checkpoint(self) -> bool:
        """
        WALファイルのチェックポイント実行

        Returns:
            bool: チェックポイント成功時True

        Raises:
            SessionStoreError: チェックポイント失敗時
        """
        pass
```

#### 4.1.2 主要メソッド仕様

**`__init__(db_path: str, ttl_seconds: int = 1800)`**
- データベースパスとTTLを設定
- ディレクトリが存在しない場合は自動作成
- `_init_db()`を呼び出してテーブル初期化

**`_init_db() -> None`**
- `sessions`テーブル作成（既存の場合はスキップ）
- `idx_expires_at`インデックス作成
- WALモード設定（`PRAGMA journal_mode=WAL`）
- `PRAGMA synchronous=NORMAL` 設定
- `PRAGMA wal_autocheckpoint=1000` 設定

**`_get_connection()`**
- コンテキストマネージャー形式でDB接続を提供
- `with self._get_connection() as conn:` で使用
- 自動的にcommit/rollback、connection close処理

**`save(session_id: str, data: dict) -> bool`**
- セッションデータをJSON化して保存
- INSERT or REPLACE 構文で既存データを上書き
- `created_at`, `updated_at`, `expires_at` を自動設定
- トランザクション内で実行

**`load(session_id: str) -> Optional[dict]`**
- セッションIDでデータを検索
- 有効期限チェック（`expires_at > 現在時刻`）
- 有効期限切れの場合は自動削除してNoneを返す
- JSON文字列をdict型に復元

**`delete(session_id: str) -> bool`**
- セッションIDで削除
- 削除件数を確認して成功/失敗を返す

**`prune_expired() -> int`**
- `expires_at < 現在時刻` のセッションを一括削除
- 削除件数をログ出力
- 定期的に呼び出してストレージ容量を管理

**`wal_checkpoint() -> bool`**
- `PRAGMA wal_checkpoint(TRUNCATE)` 実行
- WALファイルをメインDBに反映しWALファイルをクリア
- 定期的に呼び出してWALファイル肥大化を防止

#### 4.1.3 エラーハンドリング

**例外クラス**:
```python
class SessionStoreError(Exception):
    """SessionStore基底例外クラス"""
    pass
```

**エラーハンドリング方針**:
- SQLite操作エラーは`SessionStoreError`でラップして再送出
- JSON変換エラーは`SessionStoreError`でラップ
- ファイルI/Oエラーは`SessionStoreError`でラップ
- すべてのエラーをログ出力

---

## 5. app.py修正設計

### 5.1 セッション書き込み箇所の置き換え

**現在のコード（363行）**:
```python
# 4. セッションに全データを保存（後続のprocess処理用）
session['csv_data'] = result['details']
```

**修正後のコード**:
```python
# 4. セッションストアに全データを保存（後続のprocess処理用）
session_store.save(session.sid, {
    'csv_data': result['details'],
    'uploaded_file_path': session.get('uploaded_file_path'),
    'uploaded_filename': session.get('uploaded_filename')
})
```

**現在のコード（559行）**:
```python
# 11. セッションに処理結果を保存
session['process_result'] = result_data
```

**修正後のコード**:
```python
# 11. セッションストアに処理結果を保存
session_data = session_store.load(session.sid) or {}
session_data['process_result'] = result_data
session_store.save(session.sid, session_data)
```

**現在のコード（276行）**:
```python
# 7. セッションにファイルパスを保存
session['uploaded_file_path'] = file_path
session['uploaded_filename'] = filename
```

**修正後のコード**:
```python
# 7. セッションストアにファイルパスを保存
session_data = session_store.load(session.sid) or {}
session_data['uploaded_file_path'] = file_path
session_data['uploaded_filename'] = filename
session_store.save(session.sid, session_data)
```

### 5.2 セッション読み込み箇所の置き換え

**現在のコード（333行）**:
```python
# 1. セッションからファイルパス取得
file_path = session.get('uploaded_file_path')
```

**修正後のコード**:
```python
# 1. セッションストアからファイルパス取得
session_data = session_store.load(session.sid) or {}
file_path = session_data.get('uploaded_file_path')
```

**現在のコード（456行）**:
```python
# 3. セッションからCSVデータ取得
csv_data = session.get('csv_data')
```

**修正後のコード**:
```python
# 3. セッションストアからCSVデータ取得
session_data = session_store.load(session.sid) or {}
csv_data = session_data.get('csv_data')
```

**現在のコード（200行）**:
```python
# セッションから処理結果を取得
result_data = session.get('process_result')
```

**修正後のコード**:
```python
# セッションストアから処理結果を取得
session_data = session_store.load(session.sid) or {}
result_data = session_data.get('process_result')
```

### 5.3 初期化処理

**アプリケーション初期化箇所（app.pyの37行付近）**:
```python
# Flaskアプリケーション作成
app = Flask(__name__)

# 環境変数から環境名を取得（デフォルト: development）
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# CSRF保護の初期化
csrf = CSRFProtect(app)

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

### 5.4 クリーンアップ処理

**アプリケーション起動前処理（app.pyの1106行付近）**:
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

**定期クリーンアップ（オプション）**:
```python
# アップロードエンドポイント内で定期的にクリーンアップ
@app.route('/upload', methods=['POST'])
def upload():
    # ... 既存コード ...

    # 古いファイルのクリーンアップ
    cleanup_old_files(app.config['UPLOAD_FOLDER'])

    # === 追加: 古いセッションのクリーンアップ ===
    try:
        session_store.prune_expired()
    except Exception as e:
        logger.warning(f"セッションクリーンアップ中にエラー: {str(e)}")

    # ... 既存コード ...
```

### 5.5 セッション削除処理

**clear_sessionエンドポイント（947行）**:
```python
@app.route('/clear_session', methods=['POST'])
@csrf.exempt
def clear_session():
    """セッションをクリアする"""
    logger.info("セッションクリア処理を開始")

    try:
        # アップロードファイルの削除
        session_data = session_store.load(session.sid) or {}
        file_path = session_data.get('uploaded_file_path')

        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"アップロードファイルを削除: {file_path}")

        # === 修正: セッションストアからデータ削除 ===
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

## 6. config.py修正設計

### 6.1 追加設定

**Configクラス（config.py）**:
```python
class Config:
    """Flask アプリケーション設定"""

    # ... 既存設定 ...

    # === 追加: セッションストア設定 ===
    # セッションDB設定
    SESSION_DB_PATH = os.path.join('session', 'sessions.db')
    SESSION_TTL_SECONDS = int(os.environ.get('SESSION_TTL_SECONDS', '1800'))  # 30分
    SESSION_CLEANUP_INTERVAL_HOURS = int(os.environ.get('SESSION_CLEANUP_INTERVAL_HOURS', '6'))  # 6時間

    # ... 既存設定 ...
```

**環境変数対応**:
- `SESSION_TTL_SECONDS`: セッション有効期限（秒、デフォルト1800 = 30分）
- `SESSION_CLEANUP_INTERVAL_HOURS`: クリーンアップ間隔（時間、デフォルト6時間）

---

## 7. Docker設定修正

### 7.1 docker-compose.yml修正

**現在のvolumes設定**:
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
```

**修正後のvolumes設定**:
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

**追加環境変数（オプション）**:
```yaml
environment:
  # ... 既存環境変数 ...

  # === 追加: セッションストア設定 ===
  - SESSION_TTL_SECONDS=${SESSION_TTL_SECONDS:-1800}
  - SESSION_CLEANUP_INTERVAL_HOURS=${SESSION_CLEANUP_INTERVAL_HOURS:-6}
```

### 7.2 Dockerfile修正

**現在のディレクトリ作成（29行）**:
```dockerfile
# 必要ディレクトリ作成
RUN mkdir -p uploads logs config
```

**修正後のディレクトリ作成**:
```dockerfile
# 必要ディレクトリ作成
RUN mkdir -p uploads logs config session
```

### 7.3 .gitignore修正

**追加内容**:
```gitignore
# Session Store
session/*.db
session/*.db-shm
session/*.db-wal
```

---

## 8. テスト計画

### 8.1 単体テスト（`tests/test_session_store.py`）

**テストケース**:

1. **初期化テスト**
   - `test_init_creates_db_file`: DBファイルが正しく作成されるか
   - `test_init_creates_table`: テーブルが正しく作成されるか
   - `test_init_enables_wal_mode`: WALモードが有効化されるか

2. **保存テスト**
   - `test_save_new_session`: 新規セッション保存が成功するか
   - `test_save_update_session`: 既存セッション更新が成功するか
   - `test_save_large_data`: 大容量データ（100KB）の保存が成功するか
   - `test_save_special_characters`: 特殊文字を含むデータの保存が成功するか

3. **読み込みテスト**
   - `test_load_existing_session`: 既存セッションの読み込みが成功するか
   - `test_load_nonexistent_session`: 存在しないセッションはNoneを返すか
   - `test_load_expired_session`: 有効期限切れセッションは自動削除されるか
   - `test_load_large_data`: 大容量データの読み込みが成功するか

4. **削除テスト**
   - `test_delete_existing_session`: 既存セッション削除が成功するか
   - `test_delete_nonexistent_session`: 存在しないセッション削除が成功するか（エラーなし）

5. **有効期限管理テスト**
   - `test_prune_expired_sessions`: 有効期限切れセッションが削除されるか
   - `test_prune_no_expired_sessions`: 有効なセッションは削除されないか
   - `test_ttl_setting`: TTL設定が正しく反映されるか

6. **WAL管理テスト**
   - `test_wal_checkpoint`: WALチェックポイントが成功するか
   - `test_wal_file_cleanup`: WALファイルがクリーンアップされるか

7. **エラーハンドリングテスト**
   - `test_invalid_json_data`: JSON化できないデータでエラーが発生するか
   - `test_db_lock_handling`: DBロック時のエラーハンドリング
   - `test_corrupted_db_handling`: DB破損時のエラーハンドリング

### 8.2 統合テスト（app.pyとの連携）

**テストケース**:

1. **CSVアップロードフロー**
   - `test_upload_and_preview_flow`: アップロード → プレビュー → セッションストア保存
   - `test_upload_preserves_session`: アップロード後にセッションデータが保持されるか

2. **CSV処理フロー**
   - `test_process_flow`: プレビュー → 処理 → 結果保存 → 結果表示
   - `test_process_1000_records`: 1000件CSV処理時のセッションデータ保存

3. **セッションクリア**
   - `test_clear_session_removes_data`: セッションクリアでストアからデータが削除されるか

### 8.3 E2Eテスト

**テストシナリオ**:

1. **通常フロー**
   - Step 1: CSVファイル（1000件）をアップロード
   - Step 2: プレビュー取得（セッションストアに保存）
   - Step 3: 処理実行（セッションストアからデータ読み込み）
   - Step 4: 結果表示（セッションストアから結果読み込み）
   - Step 5: セッションクリア（セッションストアからデータ削除）

2. **複数ワーカーテスト**
   - Gunicorn 4ワーカーで同時アクセス
   - WALモードによる同時実行制御が正常に動作するか

3. **WAL肥大化テスト**
   - 100回のセッション保存/削除を実行
   - WALチェックポイントでWALファイルサイズが適切に管理されるか

4. **TTL有効期限テスト**
   - セッション保存後30分経過後にアクセス
   - 有効期限切れで自動削除されるか

### 8.4 パフォーマンステスト

**テスト項目**:

1. **保存性能**
   - 1000件CSV（約100KB）の保存時間: 100ms以内
   - 10,000件CSV（約1MB）の保存時間: 500ms以内

2. **読み込み性能**
   - 1000件CSVの読み込み時間: 50ms以内
   - 10,000件CSVの読み込み時間: 200ms以内

3. **クリーンアップ性能**
   - 1000セッションの有効期限切れ削除時間: 1秒以内

4. **同時アクセス**
   - 4ワーカーで10ユーザーが同時アクセス
   - エラーなく処理が完了するか

---

## 9. 実装フェーズ分割

### Phase 1: 基盤実装（2時間）

**タスク**:
1. `modules/session_store.py` 実装
   - `SessionStore`クラス実装
   - `__init__`, `_init_db`, `_get_connection` 実装
   - `save`, `load`, `delete` 実装
   - `prune_expired`, `wal_checkpoint` 実装
   - エラーハンドリング実装

2. SQLiteスキーマ初期化
   - `sessions`テーブル作成
   - `idx_expires_at`インデックス作成
   - WALモード設定

**成果物**:
- `modules/session_store.py` 完成版
- SQLiteスキーマ定義完了

**検証**:
- `session_store.py`単体テストパス
- WALモード有効化確認

---

### Phase 2: app.py統合（1.5時間）

**タスク**:
1. セッション書き込み箇所の置き換え
   - `363行`: CSVデータ保存
   - `559行`: 処理結果保存
   - `276行`: ファイルパス保存

2. セッション読み込み箇所の置き換え
   - `333行`: ファイルパス読み込み
   - `456行`: CSVデータ読み込み
   - `200行`: 処理結果読み込み

3. 初期化処理追加
   - SessionStoreインスタンス生成
   - セッションディレクトリ作成

4. クリーンアップ処理追加
   - アプリケーション起動時クリーンアップ
   - アップロードエンドポイント内クリーンアップ

5. セッション削除処理修正
   - `clear_session`エンドポイント修正

**成果物**:
- `app.py` 修正版
- `config.py` 修正版

**検証**:
- アプリケーション起動成功
- CSVアップロード → プレビュー → 処理フロー動作確認

---

### Phase 3: Docker統合（1時間）

**タスク**:
1. `docker-compose.yml` 修正
   - セッションDBボリューム追加
   - 環境変数追加（オプション）

2. `Dockerfile` 修正
   - セッションディレクトリ作成

3. `.gitignore` 修正
   - セッションDBファイル除外

**成果物**:
- `docker-compose.yml` 修正版
- `Dockerfile` 修正版
- `.gitignore` 修正版

**検証**:
- Dockerコンテナビルド成功
- Dockerコンテナ起動成功
- セッションストア動作確認

---

### Phase 4: テスト（2時間）

**タスク**:
1. 単体テスト実装
   - `tests/test_session_store.py` 作成
   - 全テストケース実装

2. 統合テスト実装
   - app.py連携テスト実装

3. E2Eテスト実施
   - 通常フロー確認
   - 複数ワーカーテスト
   - WAL肥大化テスト
   - TTL有効期限テスト

4. パフォーマンステスト実施
   - 保存/読み込み性能測定
   - クリーンアップ性能測定
   - 同時アクセステスト

**成果物**:
- `tests/test_session_store.py` 完成版
- テストレポート

**検証**:
- 全テストパス
- パフォーマンス目標達成

---

### Phase 5: ドキュメント（1時間）

**タスク**:
1. CLAUDE.md更新
   - セッションストア概要追加
   - 技術スタック更新（SQLite追加）
   - ディレクトリ構造更新（session/追加）

2. `.claude/02_backend/` ドキュメント作成
   - `10_session_store_specification.md` 作成
   - セッションストア仕様詳細

3. 実装完了レポート作成
   - `.claude/02_backend/11_session_store_implementation_report.md`
   - 実装内容、テスト結果、性能測定結果

**成果物**:
- CLAUDE.md更新版
- `10_session_store_specification.md`
- `11_session_store_implementation_report.md`

**検証**:
- ドキュメント完全性確認
- プロジェクト全体の一貫性確認

---

## 10. エージェント割り振り

### 10.1 backend-code-generator

**担当タスク**:

**Phase 1: 基盤実装**
- [ ] `modules/session_store.py` 実装
  - `SessionStore`クラス実装
  - 全メソッド実装（`__init__`, `save`, `load`, `delete`, `prune_expired`, `wal_checkpoint`）
  - エラーハンドリング実装
  - ロギング実装
- [ ] SQLiteスキーマ初期化コード実装
- [ ] WALモード設定実装

**Phase 2: app.py統合**
- [ ] `app.py` セッション書き込み箇所修正（3箇所）
- [ ] `app.py` セッション読み込み箇所修正（3箇所）
- [ ] `app.py` 初期化処理追加
- [ ] `app.py` クリーンアップ処理追加
- [ ] `app.py` セッション削除処理修正
- [ ] `config.py` セッションストア設定追加

**Phase 4: テスト**
- [ ] `tests/test_session_store.py` 実装
  - 全単体テストケース実装
  - 統合テストケース実装
  - パフォーマンステスト実装

**Phase 5: ドキュメント**
- [ ] `.claude/02_backend/10_session_store_specification.md` 作成
- [ ] `.claude/02_backend/11_session_store_implementation_report.md` 作成

**指示事項**:
1. **modules/session_store.py実装**:
   - 本計画書の「4. モジュール設計」を参照
   - WALモード設定は必須
   - エラーハンドリングを徹底
   - ロギングを適切に実装

2. **app.py修正**:
   - 本計画書の「5. app.py修正設計」を参照
   - 既存ロジックを壊さないように慎重に修正
   - セッションID取得は`session.sid`を使用
   - エラーハンドリングを追加

3. **config.py修正**:
   - 本計画書の「6. config.py修正設計」を参照
   - 環境変数対応を実装

4. **テスト実装**:
   - 本計画書の「8. テスト計画」を参照
   - 全テストケースを実装
   - E2Eテストは手動確認で補完

5. **ドキュメント作成**:
   - 本計画書を基に詳細仕様書を作成
   - 実装完了レポートにテスト結果を含める

---

### 10.2 security-compliance-auditor（必要に応じて）

**担当タスク**:

**Phase 3: Docker統合後のセキュリティレビュー**
- [ ] セッションストアのセキュリティレビュー
  - SQLiteファイルパーミッション確認
  - セッションID生成のランダム性確認
  - セッションデータの機密性確認
- [ ] `.gitignore` 設定確認
  - セッションDBファイルが確実に除外されているか

**指示事項**:
1. **セキュリティレビュー**:
   - SQLiteファイルが外部からアクセスできないことを確認
   - セッションIDがUUID v4で生成され十分なランダム性があることを確認
   - セッションデータに機密情報が含まれる場合の暗号化検討

2. **`.gitignore`レビュー**:
   - `session/*.db`, `session/*.db-shm`, `session/*.db-wal` が除外されているか確認

---

### 10.3 project-compliance-tester（必要に応じて）

**担当タスク**:

**Phase 4: E2Eテスト実施**
- [ ] 通常フロー（1000件CSV）のE2Eテスト
- [ ] 複数ワーカーテスト（Gunicorn 4ワーカー）
- [ ] WAL肥大化テスト（100回保存/削除）
- [ ] TTL有効期限テスト（30分経過後アクセス）
- [ ] パフォーマンステスト実施
  - 1000件CSV保存/読み込み性能測定
  - クリーンアップ性能測定

**指示事項**:
1. **E2Eテスト**:
   - 本計画書の「8.3 E2Eテスト」を参照
   - 実際のDocker環境で実施
   - テスト結果を詳細に記録

2. **パフォーマンステスト**:
   - 本計画書の「8.4 パフォーマンステスト」を参照
   - 性能目標達成を確認
   - 性能測定結果をレポート化

---

## 11. リスク管理計画

### 11.1 ファイルロック競合

**リスク**:
- 複数ワーカーが同時にSQLiteにアクセスした際のロック競合

**対策**:
- WALモードで同時実行性を向上
- `PRAGMA busy_timeout=5000` で5秒のリトライ待機
- トランザクションタイムアウト設定
- ロック発生時のエラーハンドリング

**検証**:
- 複数ワーカーでの同時アクセステスト
- ロック競合発生時のログ確認

---

### 11.2 WALファイル肥大化

**リスク**:
- WALファイルが肥大化してストレージを圧迫

**対策**:
- `PRAGMA wal_autocheckpoint=1000` で自動チェックポイント
- 定期的に`wal_checkpoint()`メソッドを呼び出し
- アプリケーション起動時にWALチェックポイント実行

**検証**:
- WAL肥大化テスト（100回保存/削除）
- WALファイルサイズのモニタリング

---

### 11.3 Windows環境でのロック不安定性

**リスク**:
- Windows環境ではファイルロックが不安定な場合がある

**対策**:
- WALモードで読み取り/書き込みの分離
- `PRAGMA synchronous=NORMAL` でパフォーマンス向上
- エラー時のリトライロジック実装

**検証**:
- Windows環境でのDocker動作テスト
- ロック不安定性の監視

---

### 11.4 データ破損リスク

**リスク**:
- クラッシュ時やディスク障害時のデータ破損

**対策**:
- WALモードでクラッシュ耐性向上
- `PRAGMA integrity_check` による定期検証
- セッションデータは一時的なものなので破損時は再生成可能

**検証**:
- アプリケーション強制終了時のデータ整合性確認
- DB整合性チェックの定期実行

---

### 11.5 古いセッションデータ蓄積

**リスク**:
- 有効期限切れセッションが削除されずに蓄積

**対策**:
- `prune_expired()`メソッドの定期実行
- アプリケーション起動時にクリーンアップ
- アップロードエンドポイント内でクリーンアップ

**検証**:
- TTL有効期限テスト
- クリーンアップ処理の動作確認

---

## 12. 成果物定義

### Phase 1成果物

- [ ] `modules/session_store.py` 完成版
- [ ] SQLiteスキーマ定義完了
- [ ] 単体テスト実装（`tests/test_session_store.py`）

### Phase 2成果物

- [ ] `app.py` 修正版
- [ ] `config.py` 修正版
- [ ] 統合テスト実装

### Phase 3成果物

- [ ] `docker-compose.yml` 修正版
- [ ] `Dockerfile` 修正版
- [ ] `.gitignore` 修正版

### Phase 4成果物

- [ ] 全テストパス確認
- [ ] E2Eテスト結果レポート
- [ ] パフォーマンステスト結果レポート

### Phase 5成果物

- [ ] CLAUDE.md更新版
- [ ] `.claude/02_backend/10_session_store_specification.md`
- [ ] `.claude/02_backend/11_session_store_implementation_report.md`
- [ ] 実装完了チェックリスト

---

## 13. タイムライン

| フェーズ | タスク | 想定時間 | 累積時間 |
|---------|-------|---------|---------|
| Phase 1 | 基盤実装 | 2時間 | 2時間 |
| Phase 2 | app.py統合 | 1.5時間 | 3.5時間 |
| Phase 3 | Docker統合 | 1時間 | 4.5時間 |
| Phase 4 | テスト | 2時間 | 6.5時間 |
| Phase 5 | ドキュメント | 1時間 | 7.5時間 |
| **合計** | | **7.5時間** | |

**想定スケジュール**:
- 開始: 2025-12-30
- 完了予定: 2025-12-30（7.5時間後）

---

## 14. 実装完了チェックリスト

### Phase 1: 基盤実装

- [ ] `modules/session_store.py` 実装完了
  - [ ] `SessionStore`クラス実装
  - [ ] `__init__`メソッド実装
  - [ ] `_init_db`メソッド実装（テーブル作成、WALモード設定）
  - [ ] `_get_connection`コンテキストマネージャー実装
  - [ ] `save`メソッド実装
  - [ ] `load`メソッド実装
  - [ ] `delete`メソッド実装
  - [ ] `prune_expired`メソッド実装
  - [ ] `wal_checkpoint`メソッド実装
  - [ ] エラーハンドリング実装（`SessionStoreError`）
  - [ ] ロギング実装
- [ ] SQLiteスキーマ初期化確認
  - [ ] `sessions`テーブル作成確認
  - [ ] `idx_expires_at`インデックス作成確認
  - [ ] WALモード有効化確認

### Phase 2: app.py統合

- [ ] `app.py` 修正完了
  - [ ] セッション書き込み箇所修正（363行）
  - [ ] セッション書き込み箇所修正（559行）
  - [ ] セッション書き込み箇所修正（276行）
  - [ ] セッション読み込み箇所修正（333行）
  - [ ] セッション読み込み箇所修正（456行）
  - [ ] セッション読み込み箇所修正（200行）
  - [ ] SessionStore初期化処理追加
  - [ ] セッションディレクトリ作成処理追加
  - [ ] クリーンアップ処理追加（起動時）
  - [ ] クリーンアップ処理追加（アップロード時）
  - [ ] セッション削除処理修正（`clear_session`）
- [ ] `config.py` 修正完了
  - [ ] `SESSION_DB_PATH` 設定追加
  - [ ] `SESSION_TTL_SECONDS` 設定追加
  - [ ] `SESSION_CLEANUP_INTERVAL_HOURS` 設定追加

### Phase 3: Docker統合

- [ ] `docker-compose.yml` 修正完了
  - [ ] セッションDBボリューム追加
  - [ ] 環境変数追加（オプション）
- [ ] `Dockerfile` 修正完了
  - [ ] セッションディレクトリ作成追加
- [ ] `.gitignore` 修正完了
  - [ ] `session/*.db` 除外追加
  - [ ] `session/*.db-shm` 除外追加
  - [ ] `session/*.db-wal` 除外追加

### Phase 4: テスト

- [ ] 単体テスト実装完了（`tests/test_session_store.py`）
  - [ ] 初期化テスト（3ケース）
  - [ ] 保存テスト（4ケース）
  - [ ] 読み込みテスト（4ケース）
  - [ ] 削除テスト（2ケース）
  - [ ] 有効期限管理テスト（3ケース）
  - [ ] WAL管理テスト（2ケース）
  - [ ] エラーハンドリングテスト（3ケース）
- [ ] 統合テスト実施完了
  - [ ] CSVアップロードフロー
  - [ ] CSV処理フロー
  - [ ] セッションクリア
- [ ] E2Eテスト実施完了
  - [ ] 通常フロー（1000件CSV）
  - [ ] 複数ワーカーテスト
  - [ ] WAL肥大化テスト
  - [ ] TTL有効期限テスト
- [ ] パフォーマンステスト実施完了
  - [ ] 保存性能測定
  - [ ] 読み込み性能測定
  - [ ] クリーンアップ性能測定
  - [ ] 同時アクセステスト

### Phase 5: ドキュメント

- [ ] CLAUDE.md更新完了
  - [ ] セッションストア概要追加
  - [ ] 技術スタック更新（SQLite追加）
  - [ ] ディレクトリ構造更新（session/追加）
- [ ] `.claude/02_backend/10_session_store_specification.md` 作成完了
- [ ] `.claude/02_backend/11_session_store_implementation_report.md` 作成完了

### 最終確認

- [ ] Dockerコンテナビルド成功
- [ ] Dockerコンテナ起動成功
- [ ] CSVアップロード → プレビュー → 処理フロー動作確認
- [ ] 1000件CSV処理成功（30秒以内）
- [ ] セッションクリア動作確認
- [ ] 全テストパス確認
- [ ] パフォーマンス目標達成確認
- [ ] セキュリティレビュー完了（必要に応じて）
- [ ] ドキュメント完全性確認

---

## 15. 参考資料

### 15.1 SQLite WALモード公式ドキュメント

- [SQLite Write-Ahead Logging](https://www.sqlite.org/wal.html)
- [SQLite PRAGMA Statements](https://www.sqlite.org/pragma.html)

### 15.2 Flask Session Management

- [Flask Sessions](https://flask.palletsprojects.com/en/3.1.x/api/#sessions)
- [Flask-Session](https://flask-session.readthedocs.io/)

### 15.3 Python sqlite3モジュール

- [Python sqlite3 Documentation](https://docs.python.org/3/library/sqlite3.html)

### 15.4 プロジェクト内部ドキュメント

- `.claude/00_project/00_project_overview.md`: プロジェクト概要
- `.claude/01_development_docs/00_system_architecture.md`: システム構成
- `.claude/02_backend/00_backend_architecture.md`: バックエンドアーキテクチャ
- `.claude/02_backend/01_backend_api_routes.md`: API仕様
- `CLAUDE.md`: プロジェクト全体ガイド

---

## 16. 承認履歴

- **2025-12-30**: SQLite実装方針承認（プロジェクトオーケストレーター）
- **2025-12-30**: 実装計画作成完了（プロジェクトオーケストレーター）

---

## 17. 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|-------|
| 2025-12-30 | 1.0 | 初版作成 | Claude Code (Orchestrator) |

---

**END OF DOCUMENT**
