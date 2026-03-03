# イオンカード明細取込システム

イオンカードの利用明細CSVファイルを自動で読み込み、Googleスプレッドシートの家計簿に自動入力するシステムです。店舗名から支出カテゴリを自動判定し、手動入力の手間を大幅に削減します。

## 主な機能

- **CSVファイル自動取込**: イオンカード利用明細CSVを読み込み、データを解析
- **カテゴリ自動振り分け**: 店舗名から「外食費」「日用品費」「交通費」などのカテゴリを自動判定
- **ChatGPT自動分類（v2.0～）**: 未登録店舗をChatGPT APIで自動カテゴリ分類、ユーザー確認後にマッピング登録
- **Googleスプレッドシート自動更新**: 年別シート・月別行・カテゴリ別列に金額を自動加算
- **マッピング管理**: 店舗名とカテゴリの対応関係を簡単に登録・編集（SQLite管理）
- **未登録店舗検出**: マッピング未登録の店舗を自動検知し、新規登録を促進

## システム要件

### 必須環境
- **OS**: Windows / Mac / Linux
- **Docker Desktop**: 4.44以上
- **メモリ**: 4GB以上推奨
- **ストレージ**: 1GB以上の空き容量
- **インターネット接続**: 必須（Google Sheets API利用のため）

### 事前準備
- Googleアカウント
- Google Cloud Platformプロジェクト（サービスアカウント作成済み）
  - [サービスアカウントの作成方法](https://cloud.google.com/iam/docs/service-accounts-create)
  - [Google Sheets APIの有効化](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
- 家計簿用Googleスプレッドシート

## 環境構築手順

### 1. Docker Desktopのインストール

Docker Desktopをインストールし、起動してください。

- Windows/Mac: [Docker公式サイト](https://www.docker.com/products/docker-desktop)からダウンロード
- Linux: Docker EngineとDocker Composeをインストール

### 2. プロジェクトのクローン

```bash
git clone https://github.com/mamemaru00/Crdit_detail.git
cd Crdit_detail
```

### 3. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成します。

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

`.env`ファイルを編集し、以下の値を設定してください：

#### 環境変数一覧

| 変数名 | 必須 | 説明 | デフォルト値 |
|--------|------|------|--------------|
| `FLASK_ENV` | No | Flask実行環境（development/production）※Docker環境ではproduction推奨 | `development` |
| `SECRET_KEY` | **Yes** | セッション暗号化キー（64文字以上） | なし |
| `SPREADSHEET_ID` | No | GoogleスプレッドシートのID（省略可。メイン画面でのフォーム入力値が優先される。`/gpt/confirm` はセッション経由のフォーム入力値を使用） | なし |
| `OPENAI_API_KEY` | **Yes (v2.0)** | OpenAI APIキー（ChatGPT分類機能に必要） | なし |
| `DEFAULT_YEAR` | No | デフォルト処理年 | `2025` |
| `LOG_LEVEL` | No | ログレベル（DEBUG/INFO/WARNING/ERROR） | `INFO` |
| `CSV_MAX_FILE_SIZE` | No | CSVファイル最大サイズ（バイト） | `52428800` (50MB) |
| `SESSION_TTL_SECONDS` | No | セッション有効期限（秒） | `1800` (30分) |
| `SESSION_CLEANUP_INTERVAL_HOURS` | No | セッションクリーンアップ間隔（時間） | `6` (6時間) |
| `GPT_MODEL` | No | ChatGPTモデル名（v2.0） | `gpt-4o-mini` |
| `GPT_MAX_TOKENS` | No | ChatGPT最大トークン数（v2.0） | `2000` |
| `GPT_TEMPERATURE` | No | ChatGPT温度パラメータ（v2.0） | `0.3` |
| `GPT_BATCH_SIZE` | No | ChatGPTバッチサイズ（v2.0） | `50` |

#### 設定例

```env
# Flask設定
FLASK_ENV=production

# REQUIRED: ランダムな64文字以上の文字列を設定してください
# 生成方法（PowerShellまたはターミナルで実行）:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=ここに生成した64文字の文字列を貼り付け

# REQUIRED: GoogleスプレッドシートのスプレッドシートIDを設定してください
# 取得方法: スプレッドシートのURLから抽出
# https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
SPREADSHEET_ID=ここにスプレッドシートIDを貼り付け

# REQUIRED (v2.0): OpenAI APIキーを設定してください（ChatGPT分類機能に必要）
# 取得方法: https://platform.openai.com/api-keys
OPENAI_API_KEY=ここにOpenAI APIキーを貼り付け

# アプリケーション設定（オプション）
DEFAULT_YEAR=2025
LOG_LEVEL=INFO

# ChatGPT分類機能設定（オプション、v2.0）
GPT_MODEL=gpt-4o-mini
GPT_MAX_TOKENS=2000
GPT_TEMPERATURE=0.3
GPT_BATCH_SIZE=50
```

### 4. Google認証情報の配置

Google Cloud Platformで作成したサービスアカウントのJSONファイルを配置します。

1. `config/`ディレクトリを作成（存在しない場合）
   ```bash
   mkdir config
   ```

2. サービスアカウントのJSONファイルを`config/service_account.json`として配置
   ```bash
   # Windowsの場合
   copy ダウンロードしたファイル.json config\service_account.json

   # Mac/Linuxの場合
   cp ダウンロードしたファイル.json config/service_account.json
   ```

3. Googleスプレッドシートにサービスアカウントの編集権限を付与
   - スプレッドシートを開く
   - 右上の「共有」ボタンをクリック
   - サービスアカウントのメールアドレス（例: `creditapi@creditapi-470614.iam.gserviceaccount.com`）を追加
   - 権限を「編集者」に設定

## Docker起動方法

### コンテナの起動

```bash
docker-compose up -d
```

初回起動時はDockerイメージのビルドに数分かかります。

### 起動確認

```bash
# コンテナの状態確認
docker-compose ps

# ヘルスチェック確認（STATUSが"Up (healthy)"となればOK）
docker ps
```

### ブラウザでアクセス

ブラウザで以下のURLにアクセスしてください：

```
http://localhost:5000
```

メイン画面が表示されれば起動成功です。

### コンテナの停止

```bash
docker-compose down
```

## 使用方法

### 1. CSVファイルのアップロード

1. メイン画面（`http://localhost:5000`）にアクセス
2. 「ファイルを選択」ボタンをクリックし、イオンカード利用明細CSVファイルを選択
3. 「プレビュー」ボタンをクリックして内容を確認
4. 「処理実行」ボタンをクリック

### 2. 処理結果の確認

処理が完了すると、以下の情報が表示されます：

- **月別・カテゴリ別サマリー**: 各カテゴリの合計金額
- **未登録店舗リスト**: マッピングが未登録の店舗（ある場合）
- **処理詳細ログ**: 各明細の処理結果

### 3. マッピング管理

#### マッピング一覧の表示

1. メイン画面で「マッピング管理」ボタンをクリック
2. 登録済みの店舗名とカテゴリの一覧が表示されます

#### 新規マッピングの追加

1. マッピング管理画面で「新規追加」ボタンをクリック
2. 以下を入力：
   - **店舗名パターン**: 店舗名（例: `イオン葛西店`）
   - **カテゴリ**: 支出カテゴリ（例: `日用品費`）
   - **マッチタイプ**: `完全一致`、`前方一致`、`部分一致`から選択
   - **優先順位**: 数値が小さいほど優先（1～100）
3. 「追加」ボタンをクリック

#### マッピングの編集・削除

- **編集**: 各行の「編集」ボタンをクリックし、内容を修正後「保存」
- **削除**: 各行の「削除」ボタンをクリック

### 4. ChatGPT自動分類機能の使用（v2.0～）

#### 未登録店舗の自動分類

処理実行時に未登録店舗が検出された場合、ChatGPTで自動分類できます。

1. 処理結果画面で「未登録店舗」セクションを確認
2. 「ChatGPTで自動分類」ボタンをクリック
3. ChatGPTが店舗名から最適なカテゴリを推測し、分類結果を表示
4. 分類結果確認画面で以下を確認・編集：
   - **店舗名**: 未登録店舗の名前
   - **カテゴリ**: ChatGPTが推測したカテゴリ（ドロップダウンで変更可能）
   - **列番号**: カテゴリに対応するスプレッドシート列（C～V）
   - **金額**: その店舗の合計金額
   - **出現回数**: その店舗の明細件数
5. 必要に応じてドロップダウンでカテゴリを修正
6. 「確定」ボタンをクリックしてマッピングに登録
7. 次回以降、同じ店舗は自動的に分類されます

#### ChatGPT分類のエラー時の動作

- ChatGPT API呼び出しに失敗した場合、すべての未登録店舗はデフォルトカテゴリ（H列: 雑貨費）に分類されます
- エラー時もユーザー確認画面で手動修正が可能です

### 5. Googleスプレッドシートの確認

処理完了後、Googleスプレッドシートを確認してください。該当する年シート・月行・カテゴリ列に金額が自動加算されています。

## トラブルシューティング

### Docker起動エラー

**問題**: `docker-compose up -d`でエラーが発生する

**対処法**:
1. Docker Desktopが起動しているか確認
2. ポート5000が他のアプリケーションで使用されていないか確認
   ```bash
   # Windowsの場合
   netstat -ano | findstr :5000

   # Mac/Linuxの場合
   lsof -i :5000
   ```
3. `.env`ファイルが正しく設定されているか確認（SECRET_KEYとSPREADSHEET_IDが必須）

### Google Sheets API認証エラー

**問題**: 「認証エラー」や「権限エラー」が発生する

**対処法**:
1. `config/service_account.json`が正しく配置されているか確認
2. サービスアカウントにスプレッドシートの編集権限があるか確認
3. スプレッドシートIDが正しいか確認（`.env`ファイルのSPREADSHEET_ID）

### CSV読み込みエラー

**問題**: CSVファイルが読み込めない

**対処法**:
1. **ファイルエンコーディングの確認**: ファイルがShift_JISエンコーディングか確認
   - UTF-8の場合は変換が必要です：
     ```bash
     # Windows（PowerShell）
     Get-Content input.csv | Out-File -Encoding Default output.csv

     # Mac/Linux
     iconv -f UTF-8 -t SHIFT_JIS input.csv > output.csv
     ```
   - Excelで開いている場合：「名前を付けて保存」→「CSV（コンマ区切り）」→エンコーディング「Shift_JIS」
2. CSVフォーマットがイオンカード利用明細の形式か確認
3. ファイルサイズが50MB以下か確認（デフォルト上限）
   - より大きなファイルが必要な場合は、`.env`ファイルに以下を追加：
     ```env
     CSV_MAX_FILE_SIZE=104857600  # 100MB（バイト単位）
     ```

### ログの確認方法

```bash
# アプリケーションログの確認
docker logs aeon-card-import-system

# 最新20行のログを表示
docker logs aeon-card-import-system --tail 20

# ログをリアルタイムで監視
docker logs aeon-card-import-system -f
```

ログファイルはホスト側の`logs/app.log`にも出力されます。

### コンテナの再起動

```bash
# コンテナの停止と削除
docker-compose down

# イメージの再ビルドと起動
docker-compose up -d --build
```

## ディレクトリ構成

```
project_root/
├── app.py                      # メインアプリケーション
├── config.py                   # 設定ファイル
├── Dockerfile                  # Dockerイメージ定義
├── docker-compose.yml          # コンテナオーケストレーション
├── requirements.txt            # Python依存パッケージ
├── .env                        # 環境変数（要作成、Git管理対象外）
├── .env.example                # 環境変数テンプレート
├── config/
│   └── service_account.json   # Google認証情報（要配置、Git管理対象外）
├── data/
│   ├── mappings.db            # SQLiteマッピングDB（v2.0）
│   ├── mapping.json           # カテゴリマッピング（v1.0、廃止予定）
│   ├── backups/               # マッピングバックアップ
│   └── sessions/              # セッションストア
│       └── sessions.db        # SQLiteセッションDB
├── static/                     # フロントエンド静的ファイル
│   ├── css/style.css
│   └── js/
│       ├── index.js
│       ├── main.js
│       ├── mapping.js
│       └── gpt_classification.js  # ChatGPT分類確認用JS（v2.0）
├── templates/                  # HTMLテンプレート
│   ├── base.html
│   ├── index.html
│   ├── mapping.html
│   ├── result.html
│   └── gpt_classification.html  # ChatGPT分類確認画面（v2.0）
├── modules/                    # バックエンドモジュール
│   ├── csv_processor.py       # CSV処理
│   ├── sheets_api.py          # Google Sheets API連携
│   ├── mapping_manager.py     # マッピング管理（SQLite対応）
│   ├── category_logic.py      # カテゴリ振り分けロジック
│   ├── session_store.py       # セッションストア（SQLite）
│   └── gpt_classifier.py      # ChatGPT分類モジュール（v2.0）
├── tests/                      # テストコード
└── logs/                       # アプリケーションログ
    └── app.log
```

## 技術スタック

- **バックエンド**: Python 3.12, Flask 3.0+, pandas, Google Sheets API, OpenAI API
- **フロントエンド**: Bootstrap 5.3, JavaScript (ES6+), jQuery
- **インフラ**: Docker, Docker Compose, Gunicorn
- **データベース**: SQLite（セッションストア、マッピングDB）

## セキュリティ

- サービスアカウント認証でGoogle Sheets APIにアクセス（ブラウザ認証不要）
- OpenAI APIキー認証でChatGPT APIにアクセス（v2.0）
- 認証情報（`service_account.json`, `.env`）はGit管理対象外
- CSRF保護（全GPTエンドポイント）
- 入力バリデーション（列番号C-V範囲チェック、カテゴリ名50文字制限）
- CSVファイルは24時間後に自動クリーンアップ、またはセッションクリア時に削除
- 非rootユーザーでコンテナ実行
- セッションデータは30分でタイムアウト

## ライセンス

このプロジェクトは個人利用を目的としています。

## サポート

問題が発生した場合は、[GitHubのIssues](https://github.com/mamemaru00/Crdit_detail/issues)で報告してください。

## バージョン履歴

- **Phase 7 (v2.0)** (2026-01-31): ChatGPT自動分類機能実装完了、SQLiteマッピングDB移行、統合テスト21件全パス
- **Phase 6** (2026-01): セッション管理・セキュリティ強化
- **Phase 5** (2026-01-11): Docker化完了、Codex MCP評価A達成
- **Phase 4** (2026-01-11): バックエンドテスト完了（241ケース、100%合格）
- **Phase 3** (2025-01-08): フロントエンド実装完了
- **Phase 2** (2024-12): バックエンド実装完了
- **Phase 1** (2024-11): プロジェクト開始
