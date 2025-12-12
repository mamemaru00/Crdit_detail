# 開発ステップ（詳細版）

## Phase 1: 環境構築

### Step 1.1: プロジェクト初期化
- [x] プロジェクトルートディレクトリ作成
- [x] Gitリポジトリ初期化（`git init`）
- [x] .gitignore作成
  - service_account.json
  - credentials.json
  - *.pyc
  - __pycache__/
  - venv/
  - *.csv
  - uploads/

### Step 1.2: Python環境構築
- [x] Python 3.10以上のインストール確認
- [x] venv仮想環境作成（`python -m venv venv`）
- [x] venv有効化（Windows: `venv\Scripts\activate`, Mac/Linux: `source venv/bin/activate`）
- [x] requirements.txt作成
  ```
  Flask>=3.1.2
  pandas>=2.0.0
  gspread>=6.0.0
  google-auth>=2.23.0
  chardet>=5.0.0
  gunicorn>=23.0.0
  ```
- [x] 依存パッケージインストール（`pip install -r requirements.txt`）

### Step 1.3: ディレクトリ構造作成
- [x] 以下のディレクトリを作成
  ```
  project_root/
  ├── modules/
  ├── templates/
  ├── static/
  │   ├── css/
  │   └── js/
  └── config/
  ```

### Step 1.4: Google Cloud設定
- [x] Google Cloud Consoleでプロジェクト作成（creditapi-470614）
- [x] Google Sheets API有効化
- [x] サービスアカウント作成（creditapi@creditapi-470614.iam.gserviceaccount.com）
- [x] サービスアカウントキー（JSON）ダウンロード
- [x] `config/service_account.json`として配置
- [x] 対象スプレッドシートにサービスアカウントを編集者として共有

### Step 1.5: 設定ファイル準備
- [x] `config/mapping.json`作成（初期データ）
  ```json
  {
    "mappings": [
      {"pattern": "ユシンヤ", "match_type": "contains", "category": "外食費", "column": "C"},
      {"pattern": "AMAZON", "match_type": "contains", "category": "日用品費", "column": "D"}
    ]
  }
  ```
- [x] `config.py`作成（アプリケーション設定）

## Phase 2: バックエンド開発

### Step 2.1: CSV処理モジュール作成（modules/csv_processor.py）
- [x] ファイル読込関数実装
  - [x] Shift_JIS自動検出（chardet使用）
  - [x] UTF-8への変換処理
  - [x] エンコーディングエラーハンドリング
- [x] 明細データ抽出関数実装
  - [x] 8行目以降の行を処理
  - [x] 6桁数字で始まる行を明細として判定
  - [x] 列0（利用日）、列2（利用先）、列6（利用金額）を抽出
- [x] 日付変換関数実装
  - [x] YYMMDD形式をYYYY/MM/DD形式に変換
  - [x] 年の判定ロジック（2000年代/2050年判定）
  - [x] 月番号抽出（1-12）
- [x] プレビュー生成関数実装
  - [x] 先頭5件のデータを返す
  - [x] 辞書形式で返却（date, store, amount）
- [x] エラーハンドリング
  - [x] ファイル形式エラー
  - [x] データ欠損エラー
  - [x] 日付変換エラー

### Step 2.2: カテゴリ判定エンジン作成（modules/category_logic.py）
**完了日時**: 2025-12-11

#### 実装完了（Phase 1-6）

##### Phase 2: 基盤実装（2025-12-11完了）
- [x] 定数・型定義
  - [x] マッチタイプ定数（EXACT, STARTSWITH, CONTAINS, KEYWORD）
  - [x] デフォルト値定数（DEFAULT_COLUMN, DEFAULT_CATEGORY）
  - [x] 有効列範囲定数（VALID_COLUMNS: B～V）
  - [x] TypedDict型定義（MappingEntry, MappingData, MatchResult）
- [x] カスタム例外クラス
  - [x] CategoryLogicError（基底クラス）
  - [x] MappingLoadError（ファイル読み込みエラー）
  - [x] MappingValidationError（データ検証エラー）
  - [x] CategoryMatchError（マッチングエラー）
  - [x] InvalidMappingFormatError（形式エラー）
- [x] マッピングデータ読込関数実装（`load_mapping_data`）
  - [x] `config/mapping.json`読込
  - [x] JSON解析エラーハンドリング
  - [x] ファイル存在確認
  - [x] 必須フィールド検証（version, mappings, default）
- [x] データ検証関数実装
  - [x] `validate_mapping_entry`: 単一エントリの検証
  - [x] `validate_mapping_data`: データ全体の検証（ID重複チェック含む）

##### Phase 3: パターンマッチング実装（2025-12-11完了）
- [x] パターンマッチング関数実装
  - [x] `match_exact`: 完全一致判定（`==`）
  - [x] `match_startswith`: 前方一致判定（`startswith`）
  - [x] `match_contains`: 部分一致判定（`in`）
  - [x] `match_keyword`: キーワード一致判定（スペース区切りAND条件）
  - [x] `execute_pattern_match`: マッチング実行
- [x] 優先順位制御（完全→前方→部分→キーワードの順）
  - [x] `find_best_match`: 最適マッピング選択
  - [x] match_typeとpriorityフィールドによる二段階ソート

##### Phase 4: カテゴリ決定・未登録店舗検出（2025-12-11完了）
- [x] カテゴリ決定関数実装（`determine_category`）
  - [x] 店舗名からカテゴリ・列番号を返す
  - [x] 未登録の場合はB列（支払額）を返す
  - [x] マッチング結果をMatchResult型で返却
- [x] 未登録店舗検出関数実装（`detect_unregistered_stores`）
  - [x] マッチしなかった店舗をリスト化
  - [x] 店舗ごとの金額合計を算出
  - [x] 出現回数カウント
  - [x] 金額降順ソート
- [x] バッチ処理関数実装（`determine_categories_batch`）
  - [x] 複数レコードの一括カテゴリ判定
  - [x] カテゴリ情報付与

##### Phase 5: テスト・カバレッジ向上（2025-12-11完了）
- [x] 単体テスト作成（tests/test_category_logic.py）
  - [x] 81テストケース実装
  - [x] 全関数の正常系・異常系テスト
  - [x] エッジケーステスト
- [x] テストカバレッジ測定
  - [x] カバレッジ89%達成
  - [x] 主要ロジック100%カバー

##### Phase 6: コード品質最終確認（2025-12-11完了）
- [x] PEP 8準拠確認（100%）
  - [x] 行の長さ、インデント、命名規則
  - [x] インポート順序、空行の使用
- [x] docstring完全性確認（100%カバレッジ）
  - [x] 全12関数にdocstring
  - [x] パラメータ・戻り値・例外説明
  - [x] 使用例の記載
- [x] 型ヒント完全性確認（100%カバレッジ）
  - [x] 全パラメータ・戻り値に型ヒント
  - [x] TypedDict活用
- [x] エラーメッセージ明確性確認（優秀）
  - [x] カスタム例外とdetailsパラメータ
  - [x] 日本語メッセージ

#### 実装状況サマリー
- **実装関数数**: 12関数
- **カスタム例外**: 4クラス
- **型定義**: 3 TypedDict
- **テストケース**: 81件
- **カバレッジ**: 89%
- **コード品質**: A+（プロダクション品質）

#### 主要機能
1. **マッピングデータ管理**: JSON読み込み・検証
2. **パターンマッチング**: 4種類のマッチタイプ（完全/前方/部分/キーワード）
3. **優先順位制御**: match_typeとpriorityによる二段階ソート
4. **カテゴリ決定**: 店舗名からカテゴリ・列番号を自動判定
5. **未登録店舗検出**: 金額集計・降順ソート
6. **バッチ処理**: 複数レコードの一括処理

#### テスト結果
- **Phase 3検証**: パターンマッチング機能（2025-12-11完了）
- **Phase 4検証**: カテゴリ決定・未登録店舗検出（2025-12-11完了）
- **Phase 5検証**: テスト強化・カバレッジ向上（2025-12-11完了）

### Step 2.3: マッピング管理モジュール作成（modules/mapping_manager.py）
- [ ] マッピング一覧取得関数実装
- [ ] マッピング追加関数実装
  - バリデーション（必須項目チェック）
  - JSON書き込み
- [ ] マッピング編集関数実装
  - ID検索
  - データ更新
- [ ] マッピング削除関数実装
  - ID検索
  - データ削除
- [ ] JSON永続化処理実装
  - ファイルロック対応
  - バックアップ機能

### Step 2.4: Google Sheets API連携モジュール作成（modules/sheets_api.py）
- [ ] 認証関数実装
  - サービスアカウント認証情報読込
  - gspreadクライアント生成
  - 認証エラーハンドリング
- [ ] スプレッドシート接続関数実装
  - スプレッドシートID指定
  - 年シート存在確認
- [ ] 年シート取得関数実装
  - 利用月から年を判定
  - 該当シート検索（例：「2025年」）
  - シート未存在時のエラー処理
- [ ] 月行特定関数実装
  - 計算式：行番号 = 3 + 月番号
  - 例：8月 → 11行目
- [ ] カテゴリ列特定関数実装
  - 列名（B～V）から列番号を取得
- [ ] 既存値取得関数実装
  - セル読込
  - 空セルは0として扱う
- [ ] 金額加算関数実装
  - 既存値 + 新規金額
  - セル更新
- [ ] バ��チ更新関数実装
  - 複数セルを一度に更新
  - APIコール数削減
  - レート制限対応（待機処理）

### Step 2.5: Flaskアプリケーション作成（app.py）
- [ ] Flaskアプリ初期化
- [ ] config.py読込
- [ ] ルート定義: `GET /`
  - メイン画面表示（index.html）
- [ ] ルート定義: `POST /upload`
  - CSVファイル受信
  - 一時保存
  - ファイル検証
- [ ] ルート定義: `POST /preview`
  - CSV解析
  - プレビューデータ返却（JSON）
- [ ] ルート定義: `POST /process`
  - CSV全件処理
  - カテゴリ判定
  - Sheets更新
  - 処理結果返却（月別・カテゴリ別サマリー）
- [ ] ルート定義: `GET /mapping`
  - マッピング管理画面表示
- [ ] ルート定義: `GET /mapping/list`
  - マッピング一覧返却（JSON）
- [ ] ルート定義: `POST /mapping/add`
  - マッピング新規追加
- [ ] ルート定義: `PUT /mapping/edit/<id>`
  - マッピング編集
- [ ] ルート定義: `DELETE /mapping/delete/<id>`
  - マッピング削除
- [ ] ルート定義: `GET /download/log`
  - 処理ログダウンロード
- [ ] エラーハンドリング
  - 404, 500エラーページ
  - 例外キャッチ・ログ出力
- [ ] ファイルクリーンアップ処理
  - 処理後のCSV削除

## Phase 3: フロントエンド開発

### Step 3.1: ベーステンプレート作成（templates/base.html）
- [ ] HTML基本構造
- [ ] Bootstrap 5.3 CDN読込
- [ ] jQuery 3.7 CDN読込
- [ ] ナビゲーションバー
  - メイン画面リンク
  - マッピング管理リンク
- [ ] フッター
- [ ] コンテンツブロック定義

### Step 3.2: メイン画面作成（templates/index.html）
- [ ] ファイル選択エリア
  - `<input type="file" accept=".csv">`
  - 選択ファイル名表示
  - プレビューボタン
- [ ] プレビューテーブル
  - 利用日、店舗名、金額列
  - 最大5件表示
- [ ] スプレッドシート設定エリア
  - スプレッドシートID入力欄
  - 対象年選択ドロップダウン（2023-2026）
  - サービスアカウント情報表示
- [ ] 実行ボタンエリア
  - 「取込実行」ボタン
  - ローディング表示
- [ ] 結果表示エリア
  - 月別・カテゴリ別サマリーテーブル
  - 合計金額・処理件数表示
  - 未登録店舗リスト
  - 詳細ログダウンロードボタン

### Step 3.3: マッピング管理画面作成（templates/mapping.html）
- [ ] 検索エリア
  - 店舗名検索テキストボックス
  - 検索ボタン
- [ ] マッピング一覧テーブル
  - カラム：ID、店舗名パターン、一致方法、カテゴリ、列番号、操作
  - 編集・削除ボタン
  - ページング（10件/ページ）
- [ ] 新規追加フォーム
  - 店舗名パターン入力
  - 一致方法選択（完全/前方/部分）
  - カテゴリ選択
  - 列番号選択（B～V）
  - 登録・キャンセルボタン
- [ ] インポート・エクスポートボタン

### Step 3.4: CSS作成（static/css/style.css）
- [ ] カスタムスタイル定義
- [ ] レスポンシブ対応
- [ ] ボタンスタイル
- [ ] テーブルスタイル

### Step 3.5: JavaScript実装（static/js/main.js）
- [ ] ファイル選択イベント
  - ファイル名表示更新
- [ ] プレビューボタンクリックイベント
  - Ajax: POST /preview
  - プレビューテーブル更新
- [ ] 取込実行ボタンクリックイベント
  - Ajax: POST /process
  - ローディング表示
  - 結果表示エリア更新
- [ ] エラー表示処理
  - Alertまたはトースト表示

### Step 3.6: JavaScript実装（static/js/mapping.js）
- [ ] ページロード時処理
  - Ajax: GET /mapping/list
  - テーブル描画
- [ ] 検索機能
  - テーブルフィルタリング
- [ ] 新規追加フォーム送信
  - Ajax: POST /mapping/add
  - テーブル再読込
- [ ] 編集ボタンクリック
  - フォーム表示・データ設定
  - Ajax: PUT /mapping/edit/<id>
- [ ] 削除ボタンクリック
  - 確認ダイアログ
  - Ajax: DELETE /mapping/delete/<id>
  - テーブル再読込

## Phase 4: テスト

### Step 4.1: CSV処理テスト
- [ ] Shift_JIS読込テスト
- [ ] 日付変換テスト（各種パターン）
- [ ] 明細抽出テスト
- [ ] エラーケーステスト（不正フォーマット）

### Step 4.2: カテゴリ判定テスト
- [ ] 完全一致テスト
- [ ] 前方一致テスト
- [ ] 部分一致テスト
- [ ] 未登録店舗検出テスト

### Step 4.3: Google Sheets API連携テスト
- [ ] サービスアカウント認証テスト
- [ ] スプレッドシート接続テスト
- [ ] 年シート検索テスト
- [ ] 金額加算テスト
- [ ] エラーハンドリングテスト

### Step 4.4: 統合テスト
- [ ] エンドツーエンドテスト（CSV→Sheets更新）
- [ ] マッピング管理機能テスト
- [ ] UI操作テスト

### Step 4.5: 性能テスト
- [ ] 1000件データ処理テスト（30秒以内目標）
- [ ] 大容量ファイル（10MB）テスト

## Phase 5: Docker化

### Step 5.1: Dockerfile作成
- [ ] ベースイメージ指定（python:3.10-slim）
- [ ] 作業ディレクトリ設定
- [ ] requirements.txtコピー・インストール
- [ ] アプリケーションコードコピー
- [ ] ポート5000公開
- [ ] CMD指定（Gunicorn起動）

### Step 5.2: docker-compose.yml作成
- [ ] サービス定義（web）
- [ ] ビルド設定
- [ ] ポートマッピング（5000:5000）
- [ ] ボリュームマウント（config/, uploads/）
- [ ] 環境変数設定

### Step 5.3: Docker動作確認
- [ ] イメージビルド（`docker-compose build`）
- [ ] コンテナ起動（`docker-compose up`）
- [ ] ブラウザアクセステスト（http://localhost:5000）
- [ ] CSV取込テスト

## Phase 6: ドキュメント整備

### Step 6.1: README.md更新
- [x] プロジェクト概要
- [ ] 環境構築手順
- [ ] 使用方法
- [ ] Docker起動方法

### Step 6.2: 運用手順書作成
- [x] サービスアカウント設定手順
- [x] スプレッドシート共有手順
- [ ] CSV取込手順

### Step 6.3: トラブルシューティングガイド作成
- [x] よくあるエラーと対処法
- [ ] ログ確認方法
