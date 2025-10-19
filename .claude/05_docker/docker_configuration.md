# Docker構成概要

## 実行環境要件

### 必須ソフトウェア
- **Docker Desktop**: 4.44以上（Windows/Mac/Linux対応）
- **Docker Engine**: 27以上
- **Docker Compose**: v2以上

### システム要件
- メモリ: 最低4GB推奨
- ストレージ: 1GB以上の空き容量
- インターネット接続必須（Google Sheets API利用のため）

## コンテナ構成

### アプリケーションコンテナ
```
[Dockerコンテナ]
├── Python 3.14.0
├── Flask 3.1.2（Webアプリケーション）
├── Gunicorn 23.0以上（WSGIサーバー）
└── 必要ライブラリ
    ├── pandas（CSV解析）
    ├── gspread（Google Sheets API）
    ├── chardet（文字コード検出）
    └── その他
```

### ポート設定
- ホスト: `localhost:5000`
- コンテナ内: Flask開発サーバーまたはGunicorn

## ディレクトリマウント

```
project_root/
├── app.py
├── config/
│   ├── mapping.json          # カテゴリマッピング
│   └── service_account.json  # Google認証情報（.gitignore対象）
├── templates/
├── static/
├── modules/
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### 重要な設定
- `config/service_account.json`は環境変数またはボリュームマウントで安全に配置
- 認証情報ファイルはGit管理対象外（`.gitignore`に追加必須）

## 起動方法

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

## アクセス方法
ブラウザで `http://localhost:5000` にアクセス

## セキュリティ考慮事項
- ローカル環境での動作（外部公開なし）
- 認証情報ファイルはコンテナ内で安全に管理
- CSVファイルは処理後自動削除