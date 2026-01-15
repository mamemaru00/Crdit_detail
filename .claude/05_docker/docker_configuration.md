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

### マルチコンテナ構成（Docker Compose）
```
[Dockerコンテナ群]
├── nginxコンテナ（nginx:alpine）
│   ├── ポート80（ホスト）→ 80（コンテナ）
│   ├── gzip圧縮（JSON/CSS/JS）
│   ├── NaN→null変換フィルター（JSON応答）
│   ├── セキュリティヘッダー付与
│   │   ├ X-Content-Type-Options: nosniff
│   │   ├ X-Frame-Options: SAMEORIGIN
│   │   └ X-XSS-Protection: 1; mode=block
│   └── ファイルサイズ制限（10MB、DoS保護）
│       ↓ (内部プロキシ http://web:5000)
└── webコンテナ（Python 3.14.0）
    ├── Flask 3.1.2（Webアプリケーション）
    ├── Gunicorn 23.0以上（WSGIサーバー）
    └── 必要ライブラリ
        ├── pandas（CSV解析）
        ├── gspread（Google Sheets API）
        ├── chardet（文字コード検出）
        └── その他
```

### ポート設定
- **ホスト側**: `localhost:5000` → nginxコンテナ:80
- **コンテナ内**: nginx:80 → web:5000（Gunicorn/Flask）
- **内部通信**: Dockerネットワーク経由（http://web:5000）

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

### Nginx層でのセキュリティ対策
- **ファイルサイズ制限**: 10MB（DoS攻撃防止）
- **セキュリティヘッダー**:
  - `X-Content-Type-Options: nosniff` - MIMEタイプスニッフィング防止
  - `X-Frame-Options: SAMEORIGIN` - クリックジャッキング防止
  - `X-XSS-Protection: 1; mode=block` - XSS攻撃防止
- **JSON応答の正規化**: NaN値をnullに自動変換（クライアントエラー防止）

### アプリケーション層のセキュリティ
- ローカル環境での動作（外部公開なし）
- 認証情報ファイルはコンテナ内で安全に管理
- CSVファイルは処理後自動削除
- サービスアカウント認証（OAuth不要）