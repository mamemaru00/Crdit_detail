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


# ==================== 例外クラス ====================

class SessionStoreError(Exception):
    """SessionStore基底例外クラス"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class SessionNotFoundError(SessionStoreError):
    """セッション未検出例外"""
    pass


# ==================== SessionStoreクラス ====================

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
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self.logger = logging.getLogger(__name__)

        # ディレクトリが存在しない場合は作成
        db_dir = Path(db_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"セッションディレクトリを作成: {db_dir}")

        # データベース初期化
        self._init_db()

        self.logger.info(
            f"SessionStore初期化完了: "
            f"db_path={db_path}, ttl_seconds={ttl_seconds}"
        )

    def _init_db(self) -> None:
        """データベーステーブル初期化とWALモード設定"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # WALモード設定
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA wal_autocheckpoint=1000")
                cursor.execute("PRAGMA busy_timeout=5000")

                # sessionsテーブル作成
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL
                    )
                """)

                # 有効期限インデックス作成
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at
                    ON sessions(expires_at)
                """)

                conn.commit()

                # WALモード確認
                cursor.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                self.logger.info(f"SQLite journal_mode: {journal_mode}")

                if journal_mode.lower() != 'wal':
                    self.logger.warning(
                        f"WALモードの設定に失敗しました（現在: {journal_mode}）"
                    )

        except sqlite3.Error as e:
            raise SessionStoreError(
                f"データベース初期化に失敗しました: {str(e)}"
            )

    @contextmanager
    def _get_connection(self):
        """
        データベース接続コンテキストマネージャー

        Yields:
            sqlite3.Connection: データベース接続オブジェクト

        Raises:
            SessionStoreError: 接続エラー
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise SessionStoreError(
                f"データベース接続エラー: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

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
        try:
            # JSON変換
            data_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

            current_time = int(time.time())
            expires_at = current_time + self.ttl_seconds

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # INSERT or REPLACE構文で保存
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions
                    (session_id, data, created_at, updated_at, expires_at)
                    VALUES (?, ?,
                        COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?),
                        ?, ?)
                """, (
                    session_id,
                    data_json,
                    session_id,
                    current_time,
                    current_time,
                    expires_at
                ))

                conn.commit()

            self.logger.debug(
                f"セッション保存成功: session_id={session_id[:8]}..., "
                f"size={len(data_json)} bytes"
            )

            return True

        except (json.JSONEncodeError, TypeError) as e:
            raise SessionStoreError(
                f"セッションデータのJSON変換に失敗しました: {str(e)}"
            )
        except sqlite3.Error as e:
            raise SessionStoreError(
                f"セッション保存に失敗しました: {str(e)}"
            )

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
        try:
            current_time = int(time.time())

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # セッション取得
                cursor.execute("""
                    SELECT data, expires_at
                    FROM sessions
                    WHERE session_id = ?
                """, (session_id,))

                row = cursor.fetchone()

                if row is None:
                    self.logger.debug(
                        f"セッションが見つかりません: session_id={session_id[:8]}..."
                    )
                    return None

                data_json, expires_at = row['data'], row['expires_at']

                # 有効期限チェック
                if expires_at < current_time:
                    self.logger.debug(
                        f"セッション有効期限切れ: session_id={session_id[:8]}..., "
                        f"expired_at={expires_at}, current_time={current_time}"
                    )

                    # 有効期限切れセッションを削除
                    cursor.execute("""
                        DELETE FROM sessions WHERE session_id = ?
                    """, (session_id,))
                    conn.commit()

                    return None

                # JSON復元
                data = json.loads(data_json)

                self.logger.debug(
                    f"セッション読み込み成功: session_id={session_id[:8]}..., "
                    f"size={len(data_json)} bytes"
                )

                return data

        except json.JSONDecodeError as e:
            raise SessionStoreError(
                f"セッションデータのJSON復元に失敗しました: {str(e)}"
            )
        except sqlite3.Error as e:
            raise SessionStoreError(
                f"セッション読み込みに失敗しました: {str(e)}"
            )

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
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    DELETE FROM sessions WHERE session_id = ?
                """, (session_id,))

                deleted_count = cursor.rowcount
                conn.commit()

                if deleted_count > 0:
                    self.logger.info(
                        f"セッション削除成功: session_id={session_id[:8]}..."
                    )
                else:
                    self.logger.debug(
                        f"削除対象セッションが見つかりません: session_id={session_id[:8]}..."
                    )

                return True

        except sqlite3.Error as e:
            raise SessionStoreError(
                f"セッション削除に失敗しました: {str(e)}"
            )

    def prune_expired(self) -> int:
        """
        有効期限切れセッションを削除

        Returns:
            int: 削除されたセッション数

        Raises:
            SessionStoreError: クリーンアップ処理失敗時
        """
        try:
            current_time = int(time.time())

            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    DELETE FROM sessions WHERE expires_at < ?
                """, (current_time,))

                deleted_count = cursor.rowcount
                conn.commit()

                if deleted_count > 0:
                    self.logger.info(
                        f"有効期限切れセッションを削除: {deleted_count}件"
                    )

                return deleted_count

        except sqlite3.Error as e:
            raise SessionStoreError(
                f"有効期限切れセッションの削除に失敗しました: {str(e)}"
            )

    def wal_checkpoint(self) -> bool:
        """
        WALファイルのチェックポイント実行

        Returns:
            bool: チェックポイント成功時True

        Raises:
            SessionStoreError: チェックポイント失敗時
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                result = cursor.fetchone()

                # result: (busy, log, checkpointed)
                # busy: 0=成功, 1=ビジー
                # log: WALファイル内のページ数
                # checkpointed: チェックポイントされたページ数

                busy, log_pages, checkpointed_pages = result

                if busy == 0:
                    self.logger.info(
                        f"WALチェックポイント成功: "
                        f"log_pages={log_pages}, checkpointed_pages={checkpointed_pages}"
                    )
                    return True
                else:
                    self.logger.warning(
                        f"WALチェックポイントがビジー状態でスキップされました"
                    )
                    return False

        except sqlite3.Error as e:
            raise SessionStoreError(
                f"WALチェックポイント実行に失敗しました: {str(e)}"
            )
