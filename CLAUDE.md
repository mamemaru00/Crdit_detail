# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**プロジェクト名**: イオンカード明細取込システム（カテゴリ自動振り分け版）

**目的**: イオンカード利用明細CSVファイルを取り込み、店舗名からカテゴリを自動判定してGoogleスプレッドシートの年別シート・月別行・カテゴリ別列に金額を自動加算することで、手動入力の手間を削減し、家計簿管理を効率化する。

**想定ユーザー**: 家計簿入力者（個人ユーザー）

## Architecture Overview

### System Architecture
```
[ユーザーPC]
    ↓ (ブラウザアクセス http://localhost:5000)
[Dockerコンテナ群]
  ├ Nginxリバースプロキシ（ポート80→5000）
  │   ├ gzip圧縮（JSON/CSS/JS）
  │   ├ NaN→null変換フィルター（JSON応答）
  │   ├ セキュリティヘッダー（X-Content-Type-Options等）
  │   └ ファイルサイズ制限（10MB、DoS保護）
  │       ↓ (プロキシ http://web:5000)
  └ Webアプリケーション（Flask）
      ├ フロントエンド（Jinja2テンプレート + Bootstrap 5.3）
      └ バックエンド（Flaskルート）
          ├ CSV解析エンジン
          ├ カテゴリ判定エンジン
          ├ マッピング管理
          └ スプレッドシート連携
              ↓ (サービスアカウント認証)
      [Google Sheets API]
          ↓
      [Googleスプレッドシート]
        ├ 2025年シート
        ├ 2024年シート
        └ ...
```

### Directory Structure
```
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
│   ├── mapping.json          # カテゴリマッピング（廃止予定、v2.0でSQLite移行）
│   ├── mappings.db           # SQLiteマッピングDB（v2.0～、NEW）
│   ├── backups/              # マッピングバックアップ（.gitignore対象）
│   └── sessions/             # セッションストア（.gitignore対象）
│       └── sessions.db       # SQLiteセッションDB（.gitignore対象）
├── static/                   # フロントエンド静的ファイル
│   ├── css/
│   │   └── style.css     # カスタムCSS
│   └── js/
│       ├── main.js       # メイン画面用JS
│       ├── mapping.js    # マッピング管理用JS
│       └── gpt_classification.js  # ChatGPT分類確認用JS（v2.0～、NEW）
├── templates/                # Jinja2テンプレート
│   ├── base.html         # ベーステンプレート
│   ├── index.html        # メイン画面
│   ├── mapping.html      # マッピング管理画面
│   ├── result.html       # 処理結果画面
│   └── gpt_classification.html  # ChatGPT分類確認画面（v2.0～、NEW）
└── modules/
    ├── csv_processor.py  # CSV処理モジュール
    ├── sheets_api.py     # Sheets API連携
    ├── mapping_manager.py # マッピング管理（v2.0でSQLite対応）
    ├── category_logic.py  # カテゴリ振り分けロジック
    ├── session_store.py   # セッションストア（SQLite）
    └── gpt_classifier.py  # ChatGPT分類モジュール（v2.0～、NEW）
```

## Technology Stack

### Backend
- **Python**: 3.10+ (Docker: 3.12-slim-bookworm, LTS 2028年まで)
- **Flask**: 3.0+ (推奨 3.1.2)
- **pandas**: 2.0+ (CSV処理・データ操作)
- **google-api-python-client**: 2.100+ (Google Sheets API連携)
- **google-auth**: 2.23+ (OAuth認証)
- **gspread**: 6.x (Google Sheets連携)
- **chardet**: 文字コード検出
- **python-dotenv**: 1.0+ (環境変数管理、.env読み込み)
- **SQLite**: 3.x (セッションストア、マッピングDB、WALモード対応)
- **OpenAI API**: GPT-5-mini (未登録店舗の自動カテゴリ分類、v2.0～、v2.1でコスト最適化)

### Frontend
- **Bootstrap**: 5.3 (UIフレームワーク)
- **JavaScript**: ES6+
- **jQuery**: 3.7+
- **Jinja2**: 3.1+ (テンプレートエンジン)

### Infrastructure
- **Docker Desktop**: 4.44以上
- **Docker Engine**: 27以上
- **Docker Compose**: v2以上
- **Gunicorn**: 23.0以上（WSGIサーバー）

### API & Authentication
- **Google Sheets API v4**: スプレッドシート操作
- **サービスアカウント認証**: API認証方式（ブラウザ認証不要）
- **サービスアカウントメール**: creditapi@creditapi-470614.iam.gserviceaccount.com
- **プロジェクトID**: creditapi-470614

### Data Management
- **JSON**: マッピングデータ保存
- **Google Sheets**: 家計簿データ管理
- **ローカルストレージ**: 一時ファイル保存

## Development Commands

### Docker Operations
```bash
# イメージビルド
docker-compose build

# コンテナ起動
docker-compose up

# バックグラウンド起動
docker-compose up -d

# 停止
docker-compose down
```

### Application Access
ブラウザで `http://localhost:5000` にアクセス

### Environment Variables

**`.env`ファイルによる環境変数管理（推奨）**:
プロジェクトルートに`.env`ファイルを作成し、以下の環境変数を設定します。`.env.example`をコピーして使用してください。

```bash
# .envファイル例
# OpenAI API設定（ChatGPT分類機能 v2.0）
OPENAI_API_KEY=your-api-key-here
GPT_MODEL=gpt-5-mini  # v2.1: コスト最適化（gpt-5→gpt-5-mini、5倍削減）
GPT_MAX_TOKENS=1500  # v2.1: 出力コスト削減（2000→1500）
GPT_TEMPERATURE=1.0  # v2.1: gpt-5-miniはtemperature=1.0のみサポート（0.3等は400エラー）
GPT_BATCH_SIZE=10  # v2.1: Rate Limit対策（50→10、Issue #73で変更）
GPT_BATCH_DELAY_SECONDS=3  # v2.1: バッチ間遅延（Rate Limit対策、Issue #75）

# Flask設定
SECRET_KEY=your-secret-key-here

# Google Sheets設定
SPREADSHEET_ID=your-spreadsheet-id-here

# アプリケーション設定
DEFAULT_YEAR=2025
LOG_LEVEL=INFO
SESSION_TTL_SECONDS=1800
CSV_MAX_FILE_SIZE=10485760  # 10MB（デフォルト）

# CSVファイルサイズ上限設定（オプション）
# デフォルト: 10MB (10485760 bytes)
# テスト用: 20MB (20971520 bytes)
# 本番推奨: 10MB（セキュリティ重視）
```

**注意事項**:
- `.env`ファイルは`.gitignore`で管理対象外です（機密情報保護）
- `.env.example`はテンプレートファイルで、Git管理対象です
- `python-dotenv`ライブラリが自動的に`.env`を読み込みます
- Docker環境では`docker-compose.yml`の`env_file`設定で`.env`を読み込みます

**従来の環境変数設定（Mac/Linux）**:
```bash
# CSVファイルサイズ上限設定（オプション）
export CSV_MAX_FILE_SIZE=20971520  # 20MB
```

**従来の環境変数設定（Windows）**:
```bash
# CSVファイルサイズ上限設定（オプション）
set CSV_MAX_FILE_SIZE=20971520  # 20MB
```

### Python Development (venv)
```bash
# 仮想環境作成
python -m venv venv

# 仮想環境有効化 (Windows)
venv\Scripts\activate

# 仮想環境有効化 (Mac/Linux)
source venv/bin/activate

# 依存パッケージインストール
pip install -r requirements.txt

# Flask開発サーバー起動
python app.py
```

## Key Features

1. **CSVファイル取込**
   - Shift_JISエンコーディングの利用明細CSVをアップロード・解析
   - 6桁日付（YYMMDD）→ YYYY/MM/DD 変換
   - 明細データ抽出

2. **カテゴリ自動判定**
   - 店舗名から外食費、日用品費、交通費などのカテゴリを自動振り分け
   - パターンマッチング（完全一致、前方一致、部分一致）
   - 優先順位の適用（手動登録 > ChatGPT自動分類）
   - **v2.0**: SQLiteマッピングDB対応（JSON形式から移行）

3. **ChatGPT自動分類機能（v2.0～、NEW）**
   - 未登録店舗をChatGPT APIで自動カテゴリ分類
   - ユーザー確認フロー（分類結果の手修正可能）
   - SQLite一括登録（source='auto', priority=4）
   - エラー時のフォールバック処理（デフォルトカテゴリ: H列 雑貨費）
   - バッチ処理対応（最大50件/リクエスト）
   - **セキュリティ**: CSRF保護、入力バリデーション（列番号C-V、カテゴリ名50文字制限）

4. **スプレッドシート自動更新**
   - Googleスプレッドシートの該当する年・月・カテゴリに金額を自動加算
   - 年別シート選択（2025年、2024年など）
   - 月別行（1月～12月）・カテゴリ別列（C～V列）への書き込み

5. **マッピング管理**
   - 店舗名とカテゴリの対応関係を管理・編集
   - CRUD操作（登録、更新、削除）
   - **v1.0**: JSON形式でデータ永続化
   - **v2.0**: SQLite形式で高速検索・トランザクション保証

6. **未登録店舗管理**
   - マッピング未登録店舗の自動検知
   - 金額合計と処理件数の表示
   - 新規マッピング登録機能
   - **v2.0**: ChatGPT自動分類フローへの誘導

7. **セッション管理**
   - 独自server_session_id実装（Flask標準session使用）
   - SQLiteベースのサーバーサイドセッションストア
   - Cookie 4KB制限の解消（大容量CSVデータ対応）
     - Cookieには32バイトのUUID4のみ保存
     - 大容量データはSessionStoreに保存
   - セッションデータのセキュア管理
   - 自動有効期限管理（TTL: 30分、カスタマイズ可能）
   - WALモード対応（同時実行性向上）
   - Flask-Session不要（TypeErrorリスク回避）

## API Endpoints

### Main Routes
```
GET  /              # メイン画面
GET  /mapping       # マッピング管理画面
GET  /result        # 処理結果表示
```

### CSV Processing
```
POST /upload        # CSVファイルアップロード
POST /preview       # CSVプレビュー取得
POST /process       # CSV処理実行・Sheets更新
```

### Mapping Management
```
GET    /mapping/list            # マッピング一覧取得（SQLite: store_mappings）
POST   /mapping/add             # 新規マッピング追加（SQLite INSERT）
PUT    /mapping/edit/<id>       # マッピング編集（SQLite UPDATE）
DELETE /mapping/delete/<id>     # マッピング削除（SQLite DELETE）
```

### ChatGPT Classification（v2.0～、NEW）
```
POST /gpt/classify            # 未登録店舗をChatGPTで自動分類（CSRF保護）
GET  /gpt/classification      # ChatGPT分類結果確認画面を表示
POST /gpt/confirm             # ユーザー確認後、SQLiteに一括登録（CSRF保護、入力バリデーション）
POST /gpt/cancel              # ChatGPT分類をキャンセル（CSRF保護）
```

### Downloads
```
GET  /download/log  # 処理ログダウンロード
```

## Data Flow

### 従来フロー（～v1.0）
1. **CSVアップロード** → Shift_JIS → UTF-8 変換 → ファイル保存
2. **CSV解析** → 明細データ抽出 → YYMMDD → YYYY/MM/DD 変換 → プレビュー返却
3. **カテゴリ判定** → 店舗名マッピング照合（JSON） → カテゴリ・列番号決定 → 未登録店舗リスト化
4. **Google Sheets連携** → サービスアカウント認証 → 年シート・月行・カテゴリ列特定 → 金額加算
5. **結果表示** → 月別・カテゴリ別サマリー → 未登録店舗リスト → 処理詳細ログ

### ChatGPT分類フロー（v2.0～）
1. **CSVアップロード** → Shift_JIS → UTF-8 変換 → ファイル保存
2. **CSV解析** → 明細データ抽出 → YYMMDD → YYYY/MM/DD 変換 → プレビュー返却
3. **カテゴリ判定** → 店舗名マッピング照合（SQLite: store_mappings）
   - 登録済み店舗 → カテゴリ・列番号決定 → Step 7へ
   - 未登録店舗 → ChatGPT分類フローへ
4. **ChatGPT自動分類** → 未登録店舗抽出 → GPT API呼び出し → JSON分類結果受信
5. **ユーザー確認** → 分類結果一覧表示 → 手修正可能 → 確定ボタン押下
6. **SQLite登録** → 確定済み分類結果を一括INSERT（source='auto', priority=4）
7. **Google Sheets連携** → サービスアカウント認証 → 年シート・月行・カテゴリ列特定 → 金額加算
8. **結果表示** → 月別・カテゴリ別サマリー → ChatGPT分類サマリー → 未登録店舗リスト（残存分） → 処理詳細ログ

## Testing

### Backend Tests
- CSVファイル処理テスト（正常/異常ケース、大容量ファイル）
- Google Sheets API連携テスト（認証、書き込み、エラーリカバリー）
- マッピング機能テスト（パターンマッチング、CRUD操作、データ永続化）
- **v2.0**: SQLiteマッピングDBテスト（トランザクション、インデックス検索）
- **v2.0**: ChatGPT分類機能テスト（API呼び出し、エラーハンドリング、フォールバック）
- 集計処理テスト（計算ロジック、未登録店舗検知）
- 統合テスト（エンドツーエンド、性能テスト）

### Frontend Tests
- UI操作テスト（ファイルアップロード、フォーム入力）
- レスポンシブデザインテスト
- エラー表示テスト

### Performance Targets
- 1000件データ処理時間: 30秒以内
- 大容量ファイル対応: 10MB級（環境変数で上限調整可能）
- **v2.0**: ChatGPT分類処理時間: 50件で10秒以内
- **v2.0**: SQLiteマッピング検索: 1000件で1秒以内

## Security Considerations

### Environment Security
- ローカル環境での動作（外部公開なし）
- ポート5000でローカルアクセスのみ
- インターネット接続必須（Google Sheets API利用のため）

### Credential Management
- `config/service_account.json` は `.gitignore` 対象
- **v2.0**: `OPENAI_API_KEY` は環境変数で管理（`.env`ファイル、`.gitignore`対象）
- 認証情報ファイルはコンテナ内で安全に管理
- 環境変数またはボリュームマウントで配置

### Data Security
- CSVファイルは処理後自動削除
- 機密情報（credentials.json、.env等）は Git 管理対象外
- サービスアカウント認証（OAuth不要）
- **v2.0**: SQLiteマッピングDBは暗号化不要（機密情報なし）

### File Size Limits
- **デフォルト上限**: 10MB（DoS攻撃防止）
- **環境変数**: `CSV_MAX_FILE_SIZE`（バイト単位）でカスタマイズ可能
- **優先順位**:
  1. 環境変数`CSV_MAX_FILE_SIZE`
  2. Flask設定`MAX_CONTENT_LENGTH`（50MB）
  3. デフォルト10MB
- **テスト環境**: 20MBに設定可能（性能検証用）
- **本番環境**: 10MB推奨（セキュリティ重視）

## Key Conventions

### Coding Standards
- Python PEP 8準拠
- 関数・変数名は英語（コメントは日本語可）
- モジュール単位で責務を分離

### Git Workflow
- ブランチ戦略: main/master
- コミットメッセージ: 日本語または英語
- `.gitignore`: credentials.json, service_account.json, *.pyc, venv/, __pycache__/

### Documentation
- 詳細仕様は [.claude/](.claude/) 配下を参照
- プロジェクト概要: [.claude/00_project/00_project_overview.md](.claude/00_project/00_project_overview.md)
- システム構成: [.claude/01_development_docs/00_system_architecture.md](.claude/01_development_docs/00_system_architecture.md)
- バックエンドAPI: [.claude/02_backend/01_backend_api_routes.md](.claude/02_backend/01_backend_api_routes.md)
- テスト仕様: [.claude/09_test/00_backend_test_specification.md](.claude/09_test/00_backend_test_specification.md)

## AI Development Tools

### Codex MCP使用ガイドライン

Codex MCP（Model Context Protocol）は、GPT-5-Codexを活用した深い分析・複雑な推論ツールです。以下の状況で**積極的に使用**してください。

#### 使用推奨シーン

1. **リファクタリング時**
   - 大規模なコード整理（複数ファイル、100行以上の変更）
   - アーキテクチャの見直し
   - パフォーマンス最適化
   - コードの可読性・保守性向上
   ```
   例: app.pyのprocess()関数（150行以上）の分割
   ```

2. **バグ修正で3回以上失敗する時**
   - 同じバグに対して3回以上修正を試みても解決しない場合
   - 根本原因が不明な複雑なバグ
   - 複数モジュールにまたがるバグ
   - 再現性の低いバグ
   ```
   例: Google Sheets API連携エラーが繰り返し発生する場合
   ```

3. **妥当性を確認する時**
   - 設計判断の妥当性検証
   - セキュリティ要件の充足確認
   - パフォーマンス要件の達成可否
   - アーキテクチャの適切性評価
   - コード品質の総合評価
   ```
   例: Phase 2バックエンド実装の総合レビュー
   ```

#### Codex MCP使用方法

**基本的な使い方:**
```python
# Codex MCPツールを使用
mcp__codex__codex(
    prompt="具体的な質問や依頼内容",
    config={"web_search": true}  # Web検索を有効化
)
```

**使用例:**
```
- リファクタリング計画の立案
- バグの根本原因分析
- コードレビューと改善提案
- アーキテクチャ設計の妥当性評価
- セキュリティ脆弱性の検出
```

#### 二段構えアプローチ

- **Claude Code（第一段階）**: タスクの整理・具体化、プロジェクト文脈の追加
- **Codex CLI（第二段階）**: 深い分析、複雑な推論、最適解の導出

このアプローチにより、コスト効率と品質のバランスを最適化します。

#### 設定確認

Codex MCPのWeb検索機能が有効になっているか確認：
```bash
# 設定ファイル: C:\Users\kshou\.codex\config.toml
[tools]
web_search = true
```

## System Requirements

### Minimum Requirements
- メモリ: 4GB推奨
- ストレージ: 1GB以上の空き容量
- インターネット接続必須

### Supported Platforms
- Windows / Mac / Linux対応
- Docker Desktop動作環境

## Troubleshooting

### Common Issues
1. **Google Sheets API認証エラー**
   - `config/service_account.json` の配置を確認
   - サービスアカウントにスプレッドシートの編集権限があるか確認

2. **CSV読み込みエラー**
   - ファイルエンコーディングがShift_JISか確認
   - CSVフォーマットが想定形式か確認

3. **Dockerコンテナ起動エラー**
   - Docker Desktopが起動しているか確認
   - ポート5000が他プロセスで使用されていないか確認

## Additional Resources

### Documentation Structure
- `00_project/`: プロジェクト概要・要件定義
- `01_development_docs/`: 開発ドキュメント・システム構成
- `02_backend/`: バックエンドAPI・データ定義
- `04_ui/`: 画面設計
- `05_docker/`: Docker設定
- `06_security/`: セキュリティ要件
- `07_frontend/`: フロントエンド概要
- `08_library/`: ライブラリ仕様
- `09_test/`: テスト仕様

### Phase 4 Implementation Reports
- `PHASE4_FIX_VERIFICATION_REPORT.md`: Phase 4問題修正検証レポート
- `FIELD_NAME_FIX_SUMMARY.md`: フィールド名統一修正サマリー
- `SESSION_SID_FIX_IMPLEMENTATION.md`: session.sid修正実装レポート
- `report/PHASE4_STEP4_2_CATEGORY_LOGIC_TEST_REPORT.md`: カテゴリロジックテスト検証レポート

### Contact & Support
- プロジェクト管理: GitHub Issues
- バージョン管理: Git / GitHub

### MCPする場面
- codex: バグ修正、テストする推論するときは積極的に使用する
- playwright: 画面のテストをする際に仕様してください。
- serena : 長期記憶しておきたいことが合った時に積極的に使用する