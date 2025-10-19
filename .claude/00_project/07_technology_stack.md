# 技術スタック

## 5.1 確定技術スタック

### 5.1.1 バックエンド

| 技術 | バージョン | 用途 |
|------|-----------|------|
| Python | 3.10+ | アプリケーション言語 |
| Flask | 3.0+ | Webフレームワーク |
| pandas | 2.0+ | CSV処理・データ操作 |
| google-api-python-client | 2.100+ | Google Sheets API連携 |
| google-auth | 2.23+ | OAuth認証 |

**requirements.txt**
```
Flask>=3.0.0
pandas>=2.0.0
google-api-python-client>=2.100.0
google-auth>=2.23.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
openpyxl>=3.1.0
```

### 5.1.2 フロントエンド

| 技術 | バージョン | 用途 |
|------|-----------|------|
| Bootstrap | 5.3 | UIフレームワーク |
| JavaScript | ES6+ | クライアント処理 |
| jQuery | 3.7+ | DOM操作・Ajax通信 |
| Jinja2 | 3.1+ | テンプレートエンジン |

**CDN使用**
```html
<!-- Bootstrap CSS -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">

<!-- Bootstrap JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<!-- jQuery -->
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
```

### 5.1.3 データ管理

| 技術 | 用途 |
|------|------|
| JSON | マッピングデータ保存 |
| Google Sheets | 家計簿データ管理 |
| ローカルストレージ | 一時ファイル保存 |

### 5.1.4 API・認証

| 技術 | 用途 |
|------|------|
| Google Sheets API v4 | スプレッドシート操作 |
| サービスアカウント認証 | API認証方式 |
| RESTful API | 内部API設計 |

### 5.1.5 開発・デプロイ環境

| 項目 | 選択技術 |
|------|---------|
| OS | Windows/Linux/macOS対応 |
| Webサーバー | Flask開発サーバー（開発時）/ Gunicorn（本番時） |
| Python環境 | venv（仮想環境） |
| エディタ | Visual Studio Code推奨 |

### 5.1.6 バージョン管理・その他

| 技術 | 用途 |
|------|------|
| Git | バージョン管理 |
| GitHub | リポジトリ管理 |
| .gitignore | credentials.json等の機密情報除外 |

### 5.1.7 選定理由

- **Flask**: 軽量で学習コストが低い、拡張性が高い
- **pandas**: CSV処理に最適、データ操作が容易
- **Bootstrap**: レスポンシブ対応が容易、UIコンポーネント豊富
- **Google Sheets API**: 既存の家計簿と統合可能
- **サービスアカウント**: OAuth不要、シンプルな認証フロー