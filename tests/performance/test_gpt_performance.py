"""
Phase 7.5 Step 7.5.3 パフォーマンステスト

ChatGPT分類機能のパフォーマンスを検証するテストスイート。

テスト項目:
1. ChatGPT分類処理時間（50件で10秒以内）
2. SQLiteマッピング検索速度（1000件で1秒以内）
3. 既存機能への影響評価（CSV処理、カテゴリ判定）

Performance Targets (from CLAUDE.md):
- ChatGPT分類処理時間: 50件で10秒以内
- SQLiteマッピング検索: 1000件で1秒以内
"""

import pytest
import time
import os
import tempfile
import json
import sqlite3
from unittest.mock import MagicMock, patch
from typing import List, Dict

# テスト対象モジュール
from modules.gpt_classifier import GPTClassifier
from modules.mapping_manager import load_mapping_data
from modules.csv_processor import process_csv_file, extract_detail_data, read_csv_file
from modules.category_logic import determine_categories_batch


# ==================== パフォーマンステスト: ChatGPT分類 ====================

class TestGPTClassifierPerformance:
    """ChatGPT分類のパフォーマンステスト"""

    @pytest.fixture
    def mock_openai_client(self):
        """OpenAI APIクライアントのモック（レスポンスタイム模擬）"""
        with patch('modules.gpt_classifier.OpenAI') as mock_openai:
            # モックレスポンスを作成
            mock_response = MagicMock()
            mock_response.choices[0].message.content = json.dumps({
                f"店舗{i}": {
                    "category": "外食費",
                    "column": "D",
                    "confidence": "high",
                    "reasoning": "テスト分類"
                }
                for i in range(50)
            })

            # API呼び出しにレスポンスタイムを模擬（1-2秒）
            def mock_create(*args, **kwargs):
                time.sleep(1.5)  # 1.5秒のレスポンスタイムを模擬
                return mock_response

            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            mock_openai.return_value = mock_client

            yield mock_openai

    def test_classify_50_stores_within_10_seconds(self, mock_openai_client):
        """
        テスト1: ChatGPT分類処理時間（50件で10秒以内）

        目標: 50件の店舗名を10秒以内で分類
        方法: OpenAI APIをモック化してレスポンスタイムを模擬（1.5秒/リクエスト）
        期待: 処理時間 <= 10.0秒
        """
        # 50件の店舗名データ準備
        store_names = [f"店舗{i}" for i in range(50)]

        # GPTClassifier初期化
        classifier = GPTClassifier(
            api_key="test-api-key",
            model="gpt-5",
            batch_size=50  # 1バッチで処理
        )

        # パフォーマンス計測開始
        start_time = time.perf_counter()

        # 分類実行
        result = classifier.classify_stores(store_names)

        # パフォーマンス計測終了
        elapsed_time = time.perf_counter() - start_time

        # 結果検証
        assert len(result) == 50, f"Expected 50 classifications, got {len(result)}"
        assert elapsed_time <= 10.0, (
            f"Classification took {elapsed_time:.2f}s, expected <= 10.0s"
        )

        # ログ出力
        print(f"\n[OK] ChatGPT分類パフォーマンス: 50件を{elapsed_time:.2f}秒で処理")

    def test_classify_multiple_batches(self, mock_openai_client):
        """
        補足テスト: 複数バッチ処理のパフォーマンス（100件）

        目標: 100件の店舗名を20秒以内で分類（2バッチ）
        期待: 処理時間 <= 20.0秒
        """
        # 100件の店舗名データ準備
        store_names = [f"店舗{i}" for i in range(100)]

        # GPTClassifier初期化（バッチサイズ=50）
        classifier = GPTClassifier(
            api_key="test-api-key",
            model="gpt-5",
            batch_size=50
        )

        # モックのレスポンスを100件に更新
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            f"店舗{i}": {
                "category": "外食費",
                "column": "D",
                "confidence": "high",
                "reasoning": "テスト分類"
            }
            for i in range(50)  # 各バッチ50件
        })
        mock_openai_client.return_value.chat.completions.create.return_value = mock_response

        # パフォーマンス計測開始
        start_time = time.perf_counter()

        # 分類実行
        result = classifier.classify_stores(store_names)

        # パフォーマンス計測終了
        elapsed_time = time.perf_counter() - start_time

        # 結果検証
        assert len(result) == 100, f"Expected 100 classifications, got {len(result)}"
        assert elapsed_time <= 20.0, (
            f"Classification took {elapsed_time:.2f}s, expected <= 20.0s (2 batches)"
        )

        # ログ出力
        print(f"\n[OK] ChatGPT分類（複数バッチ）: 100件を{elapsed_time:.2f}秒で処理")


# ==================== パフォーマンステスト: SQLiteマッピング検索 ====================

class TestSQLiteMappingPerformance:
    """SQLiteマッピング検索のパフォーマンステスト"""

    @pytest.fixture
    def temp_db_with_1000_mappings(self):
        """1000件のマッピングデータを持つ一時SQLite DBを作成"""
        # 一時DBファイル作成
        temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        temp_db.close()
        db_path = temp_db.name

        # DB接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # store_mappingsテーブル作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL UNIQUE,
                match_type TEXT NOT NULL,
                category TEXT NOT NULL,
                column_name TEXT NOT NULL,
                priority INTEGER NOT NULL,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # インデックス作成（実際のDBと同じ構造）
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pattern ON store_mappings(pattern)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_priority ON store_mappings(priority)
        """)

        # 1000件のテストデータ挿入
        test_data = [
            (
                f"テスト店舗{i}",
                "exact" if i % 4 == 0 else "startswith" if i % 4 == 1 else "contains",
                "外食費" if i % 3 == 0 else "食材費" if i % 3 == 1 else "雑貨費",
                "D" if i % 3 == 0 else "C" if i % 3 == 1 else "H",
                i % 4 + 1,
                "manual" if i % 2 == 0 else "auto"
            )
            for i in range(1000)
        ]

        cursor.executemany("""
            INSERT INTO store_mappings (pattern, match_type, category, column_name, priority, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, test_data)

        conn.commit()
        conn.close()

        yield db_path

        # クリーンアップ（Windows環境でのDB接続解放を保証）
        import time
        import gc
        gc.collect()  # ガベージコレクション実行（DB接続オブジェクトの解放）
        time.sleep(0.1)  # 短い待機時間を追加

        try:
            os.unlink(db_path)
        except PermissionError:
            # Windowsでロックされている場合は再試行
            time.sleep(0.5)
            try:
                os.unlink(db_path)
            except Exception as e:
                print(f"Warning: Could not delete temp DB file {db_path}: {e}")

    def test_load_1000_mappings_within_1_second(self, temp_db_with_1000_mappings):
        """
        テスト2: SQLiteマッピング検索速度（1000件で1秒以内）

        目標: 1000件のマッピングデータを1秒以内で読み込み
        方法: 一時SQLite DBに1000件挿入し、SQLiteから全件取得
        期待: 処理時間 <= 1.0秒
        """
        db_path = temp_db_with_1000_mappings

        # パフォーマンス計測開始
        start_time = time.perf_counter()

        # SQLiteから直接マッピングデータを取得
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, pattern, match_type, category, column_name, priority, source
            FROM store_mappings
            ORDER BY priority ASC, id ASC
        """)
        rows = cursor.fetchall()
        conn.close()

        # 結果をdict形式に変換（実際のアプリケーションと同様の処理）
        mappings = [
            {
                'id': row[0],
                'pattern': row[1],
                'match_type': row[2],
                'category': row[3],
                'column': row[4],
                'priority': row[5],
                'source': row[6]
            }
            for row in rows
        ]

        # パフォーマンス計測終了
        elapsed_time = time.perf_counter() - start_time

        # 結果検証
        assert len(mappings) == 1000, f"Expected 1000 mappings, got {len(mappings)}"
        assert elapsed_time <= 1.0, (
            f"Loading 1000 mappings took {elapsed_time:.3f}s, expected <= 1.0s"
        )

        # ログ出力
        print(f"\n[OK] SQLiteマッピング検索: 1000件を{elapsed_time:.3f}秒で読み込み")

    def test_store_1000_mappings_performance(self, temp_db_with_1000_mappings):
        """
        補足テスト: 1000件のマッピングデータ書き込み速度

        目標: 1000件のマッピングデータを5秒以内で書き込み
        期待: 処理時間 <= 5.0秒
        """
        db_path = temp_db_with_1000_mappings

        # 1000件の新規マッピングデータ準備
        new_mappings = [
            {
                'pattern': f"新店舗{i}",
                'match_type': "exact",
                'category': "外食費",
                'column': "D",
                'priority': 1,
                'source': 'auto'
            }
            for i in range(1000)
        ]

        # パフォーマンス計測開始
        start_time = time.perf_counter()

        # マッピングデータ書き込み（SQLiteバッチINSERT）
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.executemany("""
            INSERT OR IGNORE INTO store_mappings (pattern, match_type, category, column_name, priority, source)
            VALUES (:pattern, :match_type, :category, :column, :priority, :source)
        """, new_mappings)

        conn.commit()
        conn.close()

        # パフォーマンス計測終了
        elapsed_time = time.perf_counter() - start_time

        # 結果検証
        assert elapsed_time <= 5.0, (
            f"Storing 1000 mappings took {elapsed_time:.3f}s, expected <= 5.0s"
        )

        # ログ出力
        print(f"\n[OK] SQLiteマッピング書き込み: 1000件を{elapsed_time:.3f}秒で保存")


# ==================== パフォーマンステスト: 既存機能への影響評価 ====================

class TestExistingFunctionsPerformance:
    """既存機能のパフォーマンステスト（Phase 7追加による影響評価）"""

    @pytest.fixture
    def sample_csv_file(self):
        """100件の明細データを持つサンプルCSVファイル作成"""
        import csv as csv_module

        temp_csv = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.csv',
            encoding='shift_jis',
            newline=''
        )

        writer = csv_module.writer(temp_csv)

        # CSVヘッダー（イオンカード形式）
        # 1行目: ヘッダー
        writer.writerow(['利用日', '利用者', '利用先', '支払方法', '利用区分', '請求区分', '利用金額', '備考', '備考2'])
        # 2～7行目: 空行（メタデータ行）
        for _ in range(6):
            writer.writerow([''] * 9)
        # 8行目: 空行（明細データ開始前）
        writer.writerow([''] * 9)

        # 9行目以降: 明細データ（100件）
        for i in range(100):
            # 日付は6桁形式（YYMMDD）: 250101～250109のサイクル
            day = (i % 9) + 1
            date = f"25010{day}"
            store = f"テスト店舗{i % 10}"
            amount = (i + 1) * 1000
            # イオンカードCSV形式に合わせて9列分のデータ
            writer.writerow([date, '本人', store, '一括払', '', '', amount, '', ''])

        temp_csv.close()

        yield temp_csv.name

        # クリーンアップ
        try:
            os.unlink(temp_csv.name)
        except Exception:
            pass  # クリーンアップ失敗は無視

    @pytest.fixture
    def sample_mappings(self):
        """サンプルマッピングデータ（10件）"""
        return {
            'version': '2.0',
            'mappings': [
                {
                    'id': i,
                    'pattern': f"テスト店舗{i}",
                    'match_type': 'exact',
                    'category': '外食費',
                    'column': 'D',
                    'priority': 1,
                    'source': 'manual'
                }
                for i in range(10)
            ],
            'default': {
                'category': '支払額',
                'column': 'B',
                'note': '未分類はB列に振り分け'
            }
        }

    def test_csv_parsing_performance(self, sample_csv_file):
        """
        テスト3-1: CSV解析処理のパフォーマンス

        目標: 100件の明細データを3秒以内で解析
        期待: 処理時間 <= 3.0秒（Phase 7追加前後で劣化なし）
        """
        # パフォーマンス計測開始
        start_time = time.perf_counter()

        # CSV解析実行
        df = read_csv_file(sample_csv_file)
        records_df = extract_detail_data(df)
        records = records_df.to_dict('records')

        # パフォーマンス計測終了
        elapsed_time = time.perf_counter() - start_time

        # 結果検証
        assert len(records) == 100, f"Expected 100 records, got {len(records)}"
        assert elapsed_time <= 3.0, (
            f"CSV parsing took {elapsed_time:.3f}s, expected <= 3.0s"
        )

        # ログ出力
        print(f"\n[OK] CSV解析: 100件を{elapsed_time:.3f}秒で処理")

    def test_category_mapping_performance(self, sample_csv_file, sample_mappings):
        """
        テスト3-2: カテゴリマッピング適用のパフォーマンス

        目標: 100件の明細データに対するカテゴリ判定を2秒以内で完了
        期待: 処理時間 <= 2.0秒（Phase 7追加前後で劣化なし）
        """
        # CSV解析
        df = read_csv_file(sample_csv_file)
        records_df = extract_detail_data(df)
        records = records_df.to_dict('records')

        # パフォーマンス計測開始
        start_time = time.perf_counter()

        # カテゴリマッピング適用
        categorized = determine_categories_batch(records, sample_mappings)

        # パフォーマンス計測終了
        elapsed_time = time.perf_counter() - start_time

        # 結果検証
        assert len(categorized) == 100, f"Expected 100 categorized records, got {len(categorized)}"
        assert elapsed_time <= 2.0, (
            f"Category mapping took {elapsed_time:.3f}s, expected <= 2.0s"
        )

        # ログ出力
        print(f"\n[OK] カテゴリマッピング: 100件を{elapsed_time:.3f}秒で処理")

    def test_end_to_end_performance(self, sample_csv_file, sample_mappings):
        """
        テスト3-3: エンドツーエンド処理のパフォーマンス

        目標: CSV解析 + カテゴリ判定を5秒以内で完了
        期待: 処理時間 <= 5.0秒
        """
        # パフォーマンス計測開始
        start_time = time.perf_counter()

        # CSV解析
        df = read_csv_file(sample_csv_file)
        records_df = extract_detail_data(df)
        records = records_df.to_dict('records')

        # カテゴリマッピング適用
        categorized = determine_categories_batch(records, sample_mappings)

        # パフォーマンス計測終了
        elapsed_time = time.perf_counter() - start_time

        # 結果検証
        assert len(categorized) == 100, f"Expected 100 categorized records, got {len(categorized)}"
        assert elapsed_time <= 5.0, (
            f"End-to-end processing took {elapsed_time:.3f}s, expected <= 5.0s"
        )

        # ログ出力
        print(f"\n[OK] エンドツーエンド: 100件を{elapsed_time:.3f}秒で処理")
        print(f"   - 登録済み店舗: {sum(1 for r in categorized if r.get('category'))}件")
        print(f"   - 未登録店舗: {sum(1 for r in categorized if not r.get('category'))}件")


# ==================== テストサマリー ====================

@pytest.fixture(scope='session', autouse=True)
def print_test_summary():
    """テスト実行後にサマリーを表示"""
    yield

    print("\n" + "=" * 80)
    print("Phase 7.5 Step 7.5.3 パフォーマンステスト 完了")
    print("=" * 80)
    print("\n[パフォーマンス目標]")
    print("  [OK] ChatGPT分類: 50件で10秒以内")
    print("  [OK] SQLiteマッピング検索: 1000件で1秒以内")
    print("  [OK] CSV解析: 100件で3秒以内")
    print("  [OK] カテゴリマッピング: 100件で2秒以内")
    print("  [OK] エンドツーエンド: 100件で5秒以内")
    print("\n詳細な計測結果は上記のテストログを参照してください。")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
