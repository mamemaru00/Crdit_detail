# CSV処理モジュール単体テスト実行手順

## Phase 4 Step 4.1: test_csv_processor.py

### テスト概要
- **テストファイル**: tests/unit/test_csv_processor.py
- **テスト対象**: modules/csv_processor.py
- **テストケース数**: 30ケース
- **カバレッジ目標**: 90%以上

### テストケース分類

#### 正常系（8ケース）
1. Shift_JIS CSVファイルのエンコーディング検出
2. UTF-8 CSVファイル正常読込
3. 日付変換（YYMMDD → YYYY/MM/DD）- 2000年代
4. 日付変換（YYMMDD → YYYY/MM/DD）- 2025年代
5. 明細データ抽出（8行目以降、6桁数字で始まる行）
6. 金額解析（カンマ区切り対応）
7. プレビューデータ生成（先頭5件）
8. 正常フロー（読込→抽出→変換→プレビュー）

#### 異常系（7ケース）
1. 空ファイル処理
2. 不正エンコーディング自動検出・変換（CP932フォールバック）
3. ヘッダーのみファイル（明細行なし）
4. 不正日付形式（5桁、7桁、英字混入）
5. 不正金額形式（英字混入）
6. 巨大ファイル（10MB以上、性能確認）
7. ファイル存在しないエラー

#### エッジケース（5ケース）
1. 金額0円
2. 金額100万円以上
3. 店舗名に特殊文字（全角スペース、半角カナ、絵文字）
4. 日付境界値（月初、月末、うるう年2月29日）
5. CSV列数不足・過多

#### ヘルパー関数テスト（10ケース）
1. is_detail_row関数のテスト
2. extract_month_number関数のテスト
3. validate_file_path関数のテスト（正常系）
4. validate_file_path関数のテスト（パストラバーサル検知）
5. generate_preview関数のテスト（5件未満）
6. generate_preview関数のテスト（空リスト）
7. 日付検証エラーのテスト（月が13）
8. 日付検証エラーのテスト（日が32）
9. 日付検証エラーのテスト（日が0）
10. 日付変換（1900年代）のテスト

### テスト実行方法

#### 方法1: バッチファイル実行（推奨）
```bash
run_csv_tests.bat
```

#### 方法2: コマンドライン実行
```bash
# 1. テストデータ生成
python encode_test_files.py

# 2. テスト実行
pytest tests/unit/test_csv_processor.py -v

# 3. カバレッジ測定
pytest tests/unit/test_csv_processor.py --cov=modules.csv_processor --cov-report=term-missing

# 4. カバレッジレポート（HTML）
pytest tests/unit/test_csv_processor.py --cov=modules.csv_processor --cov-report=html
```

### テストデータファイル

以下のファイルが`tests/fixtures/csv/`に配置されます:
- valid_shiftjis.csv - 正常データ（Shift_JIS）
- valid_utf8.csv - 正常データ（UTF-8）
- empty.csv - 空ファイル
- header_only.csv - ヘッダーのみ
- invalid_date.csv - 不正日付
- invalid_amount.csv - 不正金額
- edge_cases.csv - エッジケース
- large_file.csv - 大容量ファイル（約10MB、スクリプトで自動生成）

### 期待される結果

#### テスト結果
- 全テストケース合格（PASSED）
- 失敗ケース0件

#### カバレッジ
- 目標: 90%以上
- 対象モジュール: modules/csv_processor.py

### トラブルシューティング

#### テストデータが見つからない
```bash
# encode_test_files.pyを実行してテストデータを生成
python encode_test_files.py
```

#### エンコーディングエラー
- valid_shiftjis.csvがShift_JISでエンコードされているか確認
- encode_test_files.pyで再生成

#### 大容量ファイルテストの失敗
- large_file.csvが約10MB以上であることを確認
- ディスク空き容量を確認

### 注意事項
- テストデータはGit管理対象外（.gitignore設定済み）
- 大容量ファイルは自動生成されるため、手動での作成不要
- Shift_JISエンコーディングの検証にはWindows環境推奨
