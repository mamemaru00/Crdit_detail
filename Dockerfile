# ベースイメージ: Python 3.12-slim-bookworm（Debian 12ベース、LTS 2028年まで）
FROM python:3.12-slim-bookworm

# メタデータ
LABEL maintainer="creditapi@creditapi-470614.iam.gserviceaccount.com"
LABEL description="イオンカード明細取込システム - Dockerコンテナ版"
LABEL version="1.0"

# 作業ディレクトリ設定
WORKDIR /app

# システムパッケージ更新（セキュリティパッチ）
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# requirements.txtコピー（キャッシュ最適化）
COPY requirements.txt .

# Pythonパッケージインストール
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコードコピー
COPY . .

# 必要ディレクトリ作成
RUN mkdir -p uploads logs config data/sessions

# 非rootユーザー作成（セキュリティ強化）
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# ポート5000公開
EXPOSE 5000

# 非rootユーザーに切り替え
USER appuser

# ヘルスチェック用エンドポイント確認（start-period延長: 60s）
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Gunicornで起動（本番環境設定）
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "app:app"]
