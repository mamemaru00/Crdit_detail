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
[Dockerコンテナ]
  - Webアプリケーション（Flask）
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
├── config/
│   ├── mapping.json          # カテゴリマッピング
│   └── service_account.json  # Google認証情報（.gitignore対象）
├── static/
│   ├── css/
│   │   └── style.css     # カスタムCSS
│   └── js/
│       ├── main.js       # メイン画面用JS
│       └── mapping.js    # マッピング管理用JS
├── templates/
│   ├── base.html         # ベーステンプレート
│   ├── index.html        # メイン画面
│   ├── mapping.html      # マッピング管理画面
│   └── unregistered.html # 未登録店舗確認画面
└── modules/
    ├── csv_processor.py  # CSV処理モジュール
    ├── sheets_api.py     # Sheets API連携
    ├── mapping_manager.py # マッピング管理
    └── category_logic.py  # カテゴリ振り分けロジック
```

## Technology Stack

### Backend
- **Python**: 3.10+ (推奨 3.14.0)
- **Flask**: 3.0+ (推奨 3.1.2)
- **pandas**: 2.0+ (CSV処理・データ操作)
- **google-api-python-client**: 2.100+ (Google Sheets API連携)
- **google-auth**: 2.23+ (OAuth認証)
- **gspread**: 6.x (Google Sheets連携)
- **chardet**: 文字コード検出

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
GET    /mapping/list            # マッピング一覧取得
POST   /mapping/add             # 新規マッピング追加
PUT    /mapping/edit/<id>       # マッピング編集
DELETE /mapping/delete/<id>     # マッピング削除
```

### Downloads
```
GET  /download/log  # 処理ログダウンロード
```

## Data Flow

1. **CSVアップロード** → Shift_JIS → UTF-8 変換 → ファイル保存
2. **CSV解析** → 明細データ抽出 → YYMMDD → YYYY/MM/DD 変換 → プレビュー返却
3. **カテゴリ判定** → 店舗名マッピング照合 → カテゴリ・列番号決定 → 未登録店舗リスト化
4. **Google Sheets連携** → サービスアカウント認証 → 年シート・月行・カテゴリ列特定 → 金額加算
5. **結果表示** → 月別・カテゴリ別サマリー → 未登録店舗リスト → 処理詳細ログ

## Testing

### Backend Tests
- CSVファイル処理テスト（正常/異常ケース、大容量ファイル）
- Google Sheets API連携テスト（認証、書き込み、エラーリカバリー）
- マッピング機能テスト（パターンマッチング、CRUD操作、データ永続化）
- 集計処理テスト（計算ロジック、未登録店舗検知）
- 統合テスト（エンドツーエンド、性能テスト）

### Frontend Tests
- UI操作テスト（ファイルアップロード、フォーム入力）
- レスポンシブデザインテスト
- エラー表示テスト

### Performance Targets
- 1000件データ処理時間: 30秒以内
- 大容量ファイル対応: 10MB以上

## Security Considerations

### Environment Security
- ローカル環境での動作（外部公開なし）
- ポート5000でローカルアクセスのみ
- インターネット接続必須（Google Sheets API利用のため）

### Credential Management
- `config/service_account.json` は `.gitignore` 対象
- 認証情報ファイルはコンテナ内で安全に管理
- 環境変数またはボリュームマウントで配置

### Data Security
- CSVファイルは処理後自動削除
- 機密情報（credentials.json等）は Git 管理対象外
- サービスアカウント認証（OAuth不要）

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

### Contact & Support
- プロジェクト管理: GitHub Issues
- バージョン管理: Git / GitHub
