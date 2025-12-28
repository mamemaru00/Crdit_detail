# Phase 3 Step 3.1: バックエンド実装計画（修正版）

**最終更新日**: 2025-12-27
**ステータス**: 修正完了
**次のステップ**: Step 3.1実装（base.html作成のみ、Flask-WTF導入なし）

## 修正内容サマリー

### 修正対象問題（6件）

| ID | 重要度 | 問題内容 | 修正状況 |
|----|--------|---------|---------|
| C-1 | Critical | ルート名の不整合 | ✅ url_for()の正確なルート名を明記 |
| C-2 | Critical | Flask-WTF導入タイミング | ✅ Step 3.2以降に延期 |
| C-3 | Critical | CSRF実装方法未決定 | ✅ Meta+Fetchヘッダー方式を採用 |
| H-1 | High | python-dotenv二重管理 | ✅ Docker環境では不要と明確化 |
| H-2 | High | セキュリティヘッダー非推奨 | ✅ CSP等現代的ヘッダーに更新 |
| H-3 | High | H-4対応のタイポ修正 | ✅ Git運用手順を策定 |

---

## C-1対応: ルート名の不整合修正

### 問題の詳細

**現状の課題**:
- 実装計画書のコード例で`url_for()`のルート名が明示されていない
- app.pyの実際のルート関数名との整合性が検証されていない
- 実装時に誤ったルート名（`url_for('mapping_page')`等）を使用するリスク

**影響範囲**:
- templates/base.htmlのナビゲーションバー
- 他のテンプレートファイルでのリンク生成
- JavaScriptでのURL生成（`url_for()`をJinja2経由で使用する場合）

### 実際のルート関数名（app.py）

以下は、app.pyで定義されている実際のルート関数名です：

```python
# メインページ
@app.route('/')
def index():  # ✅ url_for('index')

# マッピング管理ページ
@app.route('/mapping')
def mapping():  # ✅ url_for('mapping')

# 処理結果ページ
@app.route('/result')
def result():  # ✅ url_for('result')

# CSVアップロードAPI
@app.route('/upload', methods=['POST'])
def upload():  # ✅ url_for('upload')

# CSVプレビューAPI
@app.route('/preview', methods=['POST'])
def preview():  # ✅ url_for('preview')

# CSV処理・Sheets更新API
@app.route('/process', methods=['POST'])
def process():  # ✅ url_for('process')

# マッピング一覧取得API
@app.route('/mapping/list', methods=['GET'])
def mapping_list():  # ✅ url_for('mapping_list')

# マッピング追加API
@app.route('/mapping/add', methods=['POST'])
def mapping_add():  # ✅ url_for('mapping_add')

# マッピング編集API
@app.route('/mapping/edit/<int:mapping_id>', methods=['PUT'])
def mapping_edit(mapping_id):  # ✅ url_for('mapping_edit', mapping_id=123)

# マッピング削除API
@app.route('/mapping/delete/<int:mapping_id>', methods=['DELETE'])
def mapping_delete(mapping_id):  # ✅ url_for('mapping_delete', mapping_id=123)

# セッションクリアAPI
@app.route('/clear_session', methods=['POST'])
def clear_session():  # ✅ url_for('clear_session')

# ログダウンロードAPI
@app.route('/download/log', methods=['GET'])
def download_log():  # ✅ url_for('download_log')
```

### 重要な注意事項

**❌ 使用してはいけないルート名**:
```python
url_for('mapping_page')  # 存在しない（正: 'mapping'）
url_for('result_page')   # 存在しない（正: 'result'）
url_for('index_page')    # 存在しない（正: 'index'）
url_for('get_mappings')  # 存在しない（正: 'mapping_list'）
url_for('add_mapping')   # 存在しない（正: 'mapping_add'）
url_for('edit_mapping')  # 存在しない（正: 'mapping_edit'）
url_for('delete_mapping') # 存在しない（正: 'mapping_delete'）
```

**✅ 正しいルート名**:
```python
url_for('index')         # メインページ
url_for('mapping')       # マッピング管理ページ
url_for('result')        # 処理結果ページ
url_for('mapping_list')  # マッピング一覧API
url_for('mapping_add')   # マッピング追加API
url_for('mapping_edit', mapping_id=123)  # マッピング編集API
url_for('mapping_delete', mapping_id=123) # マッピング削除API
```

### ナビゲーションバーの正しい実装

**templates/base.html（ナビゲーション部分）**:

```html
<nav class="navbar navbar-expand-lg navbar-dark bg-primary sticky-top">
  <div class="container-fluid">
    <!-- ブランドロゴ: メインページへのリンク -->
    <a class="navbar-brand" href="{{ url_for('index') }}">
      <i class="bi bi-credit-card"></i> Credit Detail
    </a>

    <!-- モバイルハンバーガーメニュー -->
    <button class="navbar-toggler" type="button"
            data-bs-toggle="collapse"
            data-bs-target="#mainNav"
            aria-controls="mainNav"
            aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <!-- ナビゲーションメニュー -->
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav me-auto">
        <li class="nav-item">
          <!-- メインページリンク -->
          <a class="nav-link" href="{{ url_for('index') }}">
            <i class="bi bi-house"></i> ホーム
          </a>
        </li>
        <li class="nav-item">
          <!-- マッピング管理ページリンク -->
          <a class="nav-link" href="{{ url_for('mapping') }}">
            <i class="bi bi-list-ul"></i> マッピング管理
          </a>
        </li>
      </ul>
    </div>
  </div>
</nav>
```

**重要なポイント**:
1. **`url_for('index')`**: メインページへのリンク（❌ `url_for('index_page')`ではない）
2. **`url_for('mapping')`**: マッピング管理ページへのリンク（❌ `url_for('mapping_page')`ではない）
3. **`/result`はナビゲーションに含めない**: 処理結果ページは処理後の遷移先のため、ナビゲーションバーには不要

### 実装チェックリスト（Step 3.1）

- [ ] templates/base.htmlで`url_for('index')`を使用
- [ ] templates/base.htmlで`url_for('mapping')`を使用
- [ ] `url_for('mapping_page')`や`url_for('result_page')`を使用していない
- [ ] すべての`url_for()`がapp.pyの関数名と一致している
- [ ] ナビゲーションバーに`/result`リンクが含まれていない（処理後遷移先のため）

### Step 3.2以降での追加確認項目

- [ ] templates/index.htmlで`url_for('upload')`、`url_for('preview')`、`url_for('process')`を使用
- [ ] templates/mapping.htmlで`url_for('mapping_list')`、`url_for('mapping_add')`を使用
- [ ] JavaScriptでAPI URLを生成する場合、正しいルート名を使用
- [ ] templates/result.htmlで`url_for('download_log')`を使用

---

## C-2対応: Flask-WTF導入タイミングの修正

### 問題の詳細

**現状の課題**:
- Step 3.1ではbase.html作成のみ（フォーム未実装）
- Flask-WTFを導入すると、CSRFProtectがグローバルに有効化される
- 既存のJSON API（POST /upload, POST /process等）が全て動作不可になる
  - 理由: リクエストにCSRFトークンが含まれていないため

**影響範囲**:
- Phase 2で実装済みの全POSTエンドポイント（7個）
- PUT/DELETEエンドポイント（2個）
- 計9エンドポイントが即座に動作不可

### 修正方針

**Flask-WTFの段階的導入戦略**:

#### Option A: 完全延期（推奨案）
- **Step 3.1**: Flask-WTF導入なし、requirements.txtへの追加も見送り
- **Step 3.2**: フォーム実装時にFlask-WTF + CSRF保護を同時導入
- **メリット**: 既存APIが壊れない、シンプル
- **デメリット**: Step 3.2での導入作業が増える

#### Option B: 段階的導入（代替案）
- **Step 3.1**: Flask-WTFをrequirements.txtに追加するが、`WTF_CSRF_ENABLED=False`で無効化
- **Step 3.2**: `WTF_CSRF_ENABLED=True`に変更 + JSON API向けCSRF対応実装
- **メリット**: ライブラリのバージョン固定が早期に可能
- **デメリット**: 無効化されたライブラリが存在する過渡期が生じる

### 採用案: Option A（完全延期）

**理由**:
1. Step 3.1はテンプレート骨格作成のみ（フォーム機能なし）
2. 使用しないライブラリを含めるのはアンチパターン
3. Docker環境でのイメージビルド時間短縮
4. 依存関係の最小化（セキュリティ観点）

**実装タイミング**:
```
Step 3.1: Flask-WTFなし、base.htmlのみ作成
    ↓
Step 3.2: Flask-WTF導入 + CSRF設計実装（Meta+Fetchヘッダー方式）
    ↓
Step 3.3以降: フォーム機能実装
```

---

## C-3対応: CSRF実装設計書（Step 3.2向け）

### CSRF実装方式の比較

| 方式 | メリット | デメリット | 評価 |
|------|---------|-----------|------|
| **Meta+Fetchヘッダー** | Jinja2と相性良い、実装シンプル | XSS脆弱性があるとトークン漏洩 | ✅ 採用 |
| Cookie Double Submit | DOM操作不要 | SameSite=Strict+HTTPS必須 | ❌ 過剰 |
| カスタムヘッダー | SPA向け | ハンドシェイクエンドポイント必要 | ❌ 複雑 |

### 採用方式: Meta+Fetchヘッダー

**採用理由**:
1. Jinja2テンプレート環境で同一オリジン（XSS対策が前提）
2. フォーム（hidden input）とJSON API（Fetchヘッダー）で同一トークン使用可能
3. CSPと組み合わせることでXSS対策を強化
4. 既存のJavaScriptコード変更が最小限

### 実装設計（Step 3.2向け）

#### 1. バックエンド実装（app.py）

**Step 3.2-A: Flask-WTF初期化**
```python
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config.from_object(config[flask_env])

# CSRF保護初期化
csrf = CSRFProtect(app)
```

**Step 3.2-B: CSRFトークン注入（@app.context_processor）**
```python
@app.context_processor
def inject_csrf_token():
    """全テンプレートにCSRFトークンを注入"""
    from flask_wtf.csrf import generate_csrf
    return {'csrf_token': generate_csrf}
```

**Step 3.2-C: JSON APIのCSRF検証カスタマイズ**
```python
@app.before_request
def csrf_protect_json_api():
    """JSON API向けのCSRF検証（Fetchヘッダー方式）"""
    if request.method in ['POST', 'PUT', 'DELETE']:
        # JSON APIの場合、X-CSRFTokenヘッダーを検証
        if request.is_json:
            token = request.headers.get('X-CSRFToken')
            if not token:
                abort(400, description='CSRFトークンが必要です')
            # Flask-WTFが自動検証
```

**Step 3.2-D: APIエンドポイント除外（必要に応じて）**
```python
# 特定のエンドポイントをCSRF保護から除外（非推奨）
@csrf.exempt
@app.route('/api/public', methods=['POST'])
def public_api():
    # 公開APIの場合のみ使用
    pass
```

#### 2. フロントエンド実装（templates/base.html）

**Step 3.2-E: Meta タグでトークン注入**
```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- CSRFトークン注入 -->
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>{% block title %}イオンカード明細取込システム{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    {% block content %}{% endblock %}
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script>
        // グローバルCSRFトークン設定（Fetch API用）
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

#### 3. JavaScript実装（static/js/main.js）

**Step 3.2-F: Fetch APIラッパー関数**
```javascript
/**
 * CSRF保護付きFetch API
 * @param {string} url - リクエストURL
 * @param {object} options - Fetchオプション
 * @returns {Promise<Response>}
 */
async function csrfFetch(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken  // base.htmlで定義されたトークン
        },
        credentials: 'same-origin'
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };

    return fetch(url, mergedOptions);
}

// 使用例（既存のfetchを置き換え）
async function processCSV() {
    const response = await csrfFetch('/process', {
        method: 'POST',
        body: JSON.stringify({
            spreadsheet_id: document.getElementById('spreadsheet_id').value,
            target_year: parseInt(document.getElementById('target_year').value)
        })
    });
    // ...レスポンス処理
}
```

#### 4. フォーム実装（Step 3.3以降）

**Step 3.3-A: WTFormsフォームクラス定義**
```python
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class MappingForm(FlaskForm):
    """マッピング登録フォーム"""
    pattern = StringField('店舗名パターン', validators=[DataRequired(), Length(max=100)])
    match_type = SelectField('一致方法', choices=[
        ('exact', '完全一致'),
        ('startswith', '前方一致'),
        ('contains', '部分一致')
    ])
    category = StringField('カテゴリ', validators=[DataRequired()])
    column = SelectField('列番号', choices=[(c, c) for c in 'BCDEFGHIJKLMNOPQRSTUV'])
    submit = SubmitField('登録')
```

**Step 3.3-B: テンプレートでのフォームレンダリング**
```html
<form method="POST" action="{{ url_for('add_mapping') }}">
    {{ form.csrf_token }}  <!-- hidden inputとして自動生成 -->
    <div class="mb-3">
        {{ form.pattern.label(class="form-label") }}
        {{ form.pattern(class="form-control") }}
    </div>
    <!-- 他のフィールドも同様 -->
    {{ form.submit(class="btn btn-primary") }}
</form>
```

### セキュリティ考慮事項

1. **CSP設定との統合**（H-2対応と連携）
   - `script-src 'self' 'nonce-{random}'` でインラインスクリプト制御
   - base.htmlの`<script>`タグにnonce属性追加（将来的な強化）

2. **XSS対策の徹底**
   - Jinja2の自動エスケープを維持（`{{ variable }}`）
   - `| safe`フィルタの使用を最小限に

3. **トークンのライフサイクル**
   - Flask-WTFがセッションベースでトークン管理
   - `PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)`（config.py設定済み）

4. **HTTPSの推奨**（本番環境）
   - `SESSION_COOKIE_SECURE = True`（ProductionConfig設定済み）

### 実装チェックリスト（Step 3.2）

- [ ] requirements.txtにFlask-WTF==1.2.1追加
- [ ] config.pyにWTF_CSRF_ENABLED設定追加（デフォルトTrue）
- [ ] app.pyにCSRFProtect初期化
- [ ] app.pyに@app.context_processor実装
- [ ] base.htmlに`<meta name="csrf-token">`追加
- [ ] main.jsにcsrfFetch()関数実装
- [ ] 既存のfetch()をcsrfFetch()に置き換え（7箇所）
- [ ] Playwright MCPでCSRF動作確認テスト

---

## H-1対応: python-dotenv使用ガイドライン

### 環境別の設定方針

| 環境 | python-dotenv使用 | 設定方法 | 理由 |
|------|-------------------|---------|------|
| **Docker** | ❌ 使用しない | docker-compose.ymlの`environment`セクション | 12-Factor App準拠 |
| **ローカルCLI開発** | ✅ 使用する | `.env`ファイル + `load_dotenv()` | 開発効率化 |

### Docker環境での設定方法

**docker-compose.yml**（既存実装、変更不要）:
```yaml
services:
  web:
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
      - SPREADSHEET_ID=${SPREADSHEET_ID}
      - DEFAULT_YEAR=${DEFAULT_YEAR:-2025}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - PYTHONUNBUFFERED=1
      - RUNNING_IN_DOCKER=1  # 環境識別用フラグ
```

**実装方針**:
1. docker-compose.ymlが`.env`を読み込む（Docker Composeの標準機能）
2. 環境変数としてコンテナに注入
3. Pythonコードは`os.environ`から直接読み取る
4. `python-dotenv`は不要（requirements.txtに含めない）

### ローカルCLI開発環境での設定方法

**要件**:
- venv環境で`python app.py`を直接実行する場合
- Docker非使用のローカル開発環境

**python-dotenv導入方法**（Step 3.2以降で実施）:

**1. requirements.txt修正（オプション）**:
```
# 既存の依存関係
Flask==3.1.2
pandas==2.2.0
...

# ローカル開発用（Dockerでは使用しない）
python-dotenv==1.0.0
```

**2. app.py修正（条件付き読み込み）**:
```python
import os
from pathlib import Path

# 環境検出: Docker環境ではdotenvを読み込まない
RUNNING_IN_DOCKER = os.getenv('RUNNING_IN_DOCKER', '0') == '1'

if not RUNNING_IN_DOCKER and Path('.env').exists():
    from dotenv import load_dotenv
    load_dotenv(override=False)  # 既存の環境変数を優先
    print('[INFO] .envファイルを読み込みました（ローカル開発モード）')

from flask import Flask
from config import config

# 環境変数から設定取得
flask_env = os.environ.get('FLASK_ENV', 'development')
app = Flask(__name__)
app.config.from_object(config[flask_env])
```

**3. .env.example（テンプレート）**（既存実装、変更不要）:
```bash
# Flask設定
FLASK_ENV=development

# セキュリティ設定（ランダムな値に変更してください）
SECRET_KEY=your-secret-key-here

# Google Sheets設定
SPREADSHEET_ID=your-spreadsheet-id-here

# アプリケーション設定
DEFAULT_YEAR=2025
LOG_LEVEL=INFO
```

### 12-Factor App準拠の確認

**原則3: Config（設定）**:
> 設定を環境変数に格納する

**準拠状況**:
- ✅ SECRET_KEY: 環境変数
- ✅ SPREADSHEET_ID: 環境変数
- ✅ DEFAULT_YEAR: 環境変数（デフォルト値あり）
- ✅ LOG_LEVEL: 環境変数（デフォルト値あり）
- ✅ config/service_account.json: ボリュームマウント（.dockerignore除外）

### 優先順位の明確化

**設定値の優先順位**（高→低）:
1. 実環境変数（export FOO=bar）
2. docker-compose.ymlのenvironmentセクション
3. .envファイル（`load_dotenv(override=False)`）
4. config.pyのデフォルト値

### 実装ガイドライン

**Docker環境**:
```python
# app.py冒頭
import os
# dotenvは不要、os.environから直接読み取り
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
```

**ローカルCLI開発**:
```python
# app.py冒頭
import os
from pathlib import Path

if not os.getenv('RUNNING_IN_DOCKER'):
    if Path('.env').exists():
        from dotenv import load_dotenv
        load_dotenv(override=False)

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
```

### Step 3.1での対応

**Step 3.1では変更なし**:
- 現在のapp.pyとconfig.pyは環境変数ベース（`os.environ.get()`）
- Dockerで正常動作中
- python-dotenv導入は**Step 3.2以降で検討**（必要に応じて）

---

## H-2対応: セキュリティヘッダーの現代化

### 非推奨ヘッダーの削除

**削除対象**:
- `X-XSS-Protection`: 現代ブラウザは無視または誤動作の原因
  - Chrome 78+: デフォルトで無効化
  - Edge, Firefox: 未サポート

### 推奨セキュリティヘッダー

| ヘッダー | 値 | 目的 |
|---------|---|------|
| **Content-Security-Policy** | 下記参照 | XSS対策 |
| **X-Content-Type-Options** | nosniff | MIMEスニッフィング防止 |
| **X-Frame-Options** | DENY | クリックジャッキング防止 |
| **Strict-Transport-Security** | max-age=31536000; includeSubDomains | HTTPS強制（本番のみ） |
| **Referrer-Policy** | strict-origin-when-cross-origin | リファラー制御 |
| **Permissions-Policy** | camera=(), geolocation=(), microphone=() | 機能制限 |

### Content-Security-Policy設定

#### 開発環境用CSP（緩い設定）

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com;
  style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;
  img-src 'self' data:;
  connect-src 'self' https://accounts.google.com https://sheets.googleapis.com;
  font-src 'self' https://cdn.jsdelivr.net;
  frame-ancestors 'none'
```

**許容している項目**:
- `'unsafe-inline'`: Bootstrapのインラインスタイル対応
- `'unsafe-eval'`: jQuery一部機能対応
- `https://cdn.jsdelivr.net`: Bootstrap 5.3 CDN
- `https://code.jquery.com`: jQuery 3.7+ CDN

#### 本番環境用CSP（厳格設定、将来的）

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-{random}' https://cdn.jsdelivr.net https://code.jquery.com;
  style-src 'self' 'nonce-{random}' https://cdn.jsdelivr.net;
  img-src 'self' data:;
  connect-src 'self' https://accounts.google.com https://sheets.googleapis.com;
  font-src 'self' https://cdn.jsdelivr.net;
  frame-ancestors 'none';
  upgrade-insecure-requests
```

**強化ポイント**:
- `'unsafe-inline'`削除、nonce方式採用
- `upgrade-insecure-requests`でHTTP→HTTPS強制

### 実装例（app.py）

**Step 3.1で実装**:

```python
@app.after_request
def set_security_headers(response):
    """
    セキュリティヘッダーを設定

    OWASP推奨のセキュリティヘッダーを全レスポンスに追加。
    X-XSS-Protectionは非推奨のため使用しない。
    """
    # CSP（開発環境用）
    if app.config['DEBUG']:
        # 開発環境: unsafe-inline許可（Bootstrap対応）
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self' https://accounts.google.com https://sheets.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'"
        )
    else:
        # 本番環境: 厳格設定（将来的にnonce対応）
        csp = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self' https://accounts.google.com https://sheets.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'; "
            "upgrade-insecure-requests"
        )

    response.headers['Content-Security-Policy'] = csp

    # その他のセキュリティヘッダー
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), geolocation=(), microphone=()'

    # HSTS（本番環境のみ）
    if not app.config['DEBUG']:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response
```

### CSP検証方法

**開発時の検証**:
1. Chromeデベロッパーツール → Console
2. CSP違反があると警告表示
3. 違反内容を確認して設定調整

**オンライン検証**:
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)
- CSP文字列を貼り付けて脆弱性チェック

### Step 3.1実装チェックリスト

- [ ] app.pyに`@app.after_request`デコレータ追加
- [ ] `set_security_headers()`関数実装
- [ ] X-XSS-Protectionを削除
- [ ] CSPヘッダー追加（開発/本番切り替え）
- [ ] Referrer-Policy追加
- [ ] Permissions-Policy追加
- [ ] Chromeデベロッパーツールで動作確認
- [ ] CSP Evaluatorで検証

---

## H-3対応: UI共通コンポーネント詳細仕様

### 背景

project-orchestratorの最終確認で、以下の3つのUI共通コンポーネントの具体仕様が実装計画書に欠落していることが判明しました：

1. **プログレスインジケーター**（処理中表示）
2. **トースト通知**（成功/エラーメッセージ）
3. **モーダルダイアログ**（確認ダイアログ）

本セクションでは、Bootstrap 5.3公式仕様に準拠した詳細実装仕様を定義します。

---

### 1. プログレスインジケーター（処理中表示）

#### 目的
- CSVアップロード処理（`index.html`）とマッピングCRUD/API連携（`mapping.html`）の進行状況を即座に伝える
- ユーザーに処理実行中であることを視覚的にフィードバック
- 処理完了まで追加操作を抑制する意図を明示

#### UI仕様

**使用コンポーネント**: Bootstrap 5.3 `.spinner-border`

- **サイズ**: `.spinner-border-sm`（コンパクト）
- **色**: `.text-primary`（プロジェクトのプライマリカラー）
- **ラッパー**: `.alert.alert-info.d-none`で初期非表示
- **配置場所**: `base.html`の`{% block progress %}`内で`<main>`直前に共通配置
- **デフォルト状態**: `display: none`（`.d-none`クラス）で非表示
- **文言**: 「処理中…しばらくお待ちください。」（各画面で上書き可能）

#### 表示/非表示トリガー

**表示トリガー**:
- CSV upload/preview/process APIリクエスト開始時
- マッピングCRUD操作（add/edit/delete）API開始時
- Google Sheets API連携処理開始時

**非表示トリガー**:
- 上記API処理完了時（success/error両方）
- タイムアウトエラー発生時
- ユーザーによる処理キャンセル時

#### HTML構造例

```html
{% block progress %}
<div id="progressIndicator" class="alert alert-info d-none" role="status" aria-live="polite">
  <div class="d-flex align-items-center">
    <div class="spinner-border spinner-border-sm text-primary me-2" aria-hidden="true"></div>
    <span>処理中…しばらくお待ちください。</span>
  </div>
</div>
{% endblock %}
```

**HTML構造のポイント**:
- `role="status"`: スクリーンリーダーにステータス変更を通知
- `aria-live="polite"`: ユーザーのタスクを中断せずに状態変化を伝える
- `aria-hidden="true"`: スピナーアイコン自体は装飾要素として扱う
- `.d-flex.align-items-center`: スピナーとテキストを垂直中央揃え
- `.me-2`: スピナーとテキストの間に適切なマージン（0.5rem）

#### JavaScript制御例

**jQuery版**（プロジェクト標準）:
```javascript
// グローバルAJAX開始/終了イベントで自動制御
$(document).on('ajaxStart', function() {
  $('#progressIndicator').removeClass('d-none');
});

$(document).on('ajaxStop', function() {
  $('#progressIndicator').addClass('d-none');
});

// 個別処理での制御例
function processCSV() {
  $('#progressIndicator').removeClass('d-none');

  $.ajax({
    url: '/process',
    method: 'POST',
    data: JSON.stringify({ /* ... */ }),
    contentType: 'application/json'
  })
  .done(function(response) {
    // 処理成功
  })
  .fail(function(error) {
    // エラー処理
  })
  .always(function() {
    $('#progressIndicator').addClass('d-none');
  });
}
```

**Vanilla JS版**（参考）:
```javascript
// カスタムイベントで制御
document.addEventListener('processing:start', function() {
  document.getElementById('progressIndicator').classList.remove('d-none');
});

document.addEventListener('processing:stop', function() {
  document.getElementById('progressIndicator').classList.add('d-none');
});

// Fetch APIでの使用例
async function processCSV() {
  document.dispatchEvent(new Event('processing:start'));

  try {
    const response = await fetch('/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ /* ... */ })
    });
    const data = await response.json();
    // 処理成功
  } catch (error) {
    // エラー処理
  } finally {
    document.dispatchEvent(new Event('processing:stop'));
  }
}
```

#### 重要な注意事項

1. **多重AJAX処理への対応**: 複数のAJAXリクエストが同時実行される場合、プログレスインジケーターがちらつく可能性があります。以下の対策を検討してください：
   - jQueryの`ajaxStart`/`ajaxStop`は自動的にカウンタ管理されるため推奨
   - カスタム実装の場合は、カウンタ変数で処理中リクエスト数を管理

2. **視覚的フィードバックの遅延**: ネットワークが高速な場合、スピナーが一瞬だけ表示されるとUXが悪化します。以下を推奨：
   - 最小表示時間を設定（例: 300ms）
   - 処理が300ms未満で完了した場合はスピナーを表示しない

3. **CSS駆動アニメーション**: Bootstrap 5.3のスピナーはJavaScript不要でCSS駆動します。パフォーマンスへの影響は最小限です。

#### アクセシビリティ考慮事項

1. **スクリーンリーダー対応**:
   - `role="status"`: 状態変更をアナウンス
   - `aria-live="polite"`: 現在の読み上げを中断せず、次のタイミングで通知
   - テキストメッセージを必ず含める（スピナーアイコンのみは不可）

2. **キーボード操作**:
   - プログレスインジケーター自体はフォーカス不可（静的情報）
   - 処理中は他のボタンを`disabled`属性で無効化することを推奨

3. **視覚的フィードバック**:
   - 色覚異常ユーザーへの配慮として、色だけでなくアイコン（スピナー）とテキストで状態を伝達
   - 背景色（`.alert-info`）とテキスト色のコントラスト比をWCAG AA基準（4.5:1以上）で確保

---

### 2. トースト通知（成功/エラー/警告/情報メッセージ）

#### 目的
- ユーザー操作結果を非モーダルかつ自動消失型で提示
- `index.html`: CSV処理結果（成功/エラー）、API連携結果
- `mapping.html`: CRUD操作結果（追加/編集/削除の成功/エラー）
- モーダルダイアログの代替として、軽量な通知手段を提供

#### UI仕様

**使用コンポーネント**: Bootstrap 5.3 `.toast`

- **配置場所**: `position: fixed; top: 0; right: 0;`（画面右上固定）
- **コンテナクラス**: `.toast-container.position-fixed.top-0.end-0.p-3`
- **バリエーション**: 4種類（成功/エラー/警告/情報）
- **表示時間**: 5秒後に自動非表示（Bootstrap デフォルト`delay: 5000`）
- **手動閉じ**: `.btn-close`ボタンで即座に閉じる

#### バリエーション定義

| 種類 | クラス | 用途 | アイコン（参考） |
|------|-------|------|----------------|
| **成功** | `.text-bg-success` | CRUD操作成功、CSV処理完了 | ✓ |
| **エラー** | `.text-bg-danger` | API失敗、バリデーションエラー | ✗ |
| **警告** | `.text-bg-warning` | 未登録店舗検出、データ不整合 | ⚠ |
| **情報** | `.text-bg-info` | 処理進捗、設定変更通知 | ℹ |

#### HTML構造例（4種類完全版）

```html
<!-- トーストコンテナ（base.html内） -->
<div class="toast-container position-fixed top-0 end-0 p-3" aria-live="polite" aria-atomic="true">
  {% block toasts %}

  <!-- 成功トースト -->
  <div id="successToast" class="toast align-items-center text-bg-success border-0" role="alert" aria-live="assertive" aria-atomic="true">
    <div class="d-flex">
      <div class="toast-body">
        処理が完了しました。
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto"
              data-bs-dismiss="toast" aria-label="閉じる"></button>
    </div>
  </div>

  <!-- エラートースト -->
  <div id="errorToast" class="toast align-items-center text-bg-danger border-0" role="alert" aria-live="assertive" aria-atomic="true">
    <div class="d-flex">
      <div class="toast-body">
        エラーが発生しました。
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto"
              data-bs-dismiss="toast" aria-label="閉じる"></button>
    </div>
  </div>

  <!-- 警告トースト -->
  <div id="warningToast" class="toast align-items-center text-bg-warning border-0" role="alert" aria-live="assertive" aria-atomic="true">
    <div class="d-flex">
      <div class="toast-body">
        未登録店舗が検出されました。
      </div>
      <button type="button" class="btn-close me-2 m-auto"
              data-bs-dismiss="toast" aria-label="閉じる"></button>
    </div>
  </div>

  <!-- 情報トースト -->
  <div id="infoToast" class="toast align-items-center text-bg-info border-0" role="alert" aria-live="assertive" aria-atomic="true">
    <div class="d-flex">
      <div class="toast-body">
        設定が更新されました。
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto"
              data-bs-dismiss="toast" aria-label="閉じる"></button>
    </div>
  </div>

  {% endblock %}
</div>
```

**HTML構造のポイント**:
- `role="alert"`: 重要な通知としてスクリーンリーダーに即座に伝達
- `aria-live="assertive"`: 現在の読み上げを中断して優先的にアナウンス
- `aria-atomic="true"`: 全文を一度に読み上げ（部分更新を避ける）
- `.border-0`: ボーダーを削除してフラットデザイン
- `.btn-close-white`: 成功/エラー/情報トーストの白い閉じるボタン
- `.btn-close`（通常色）: 警告トーストの黒い閉じるボタン（視認性確保）

#### JavaScript制御例

**jQuery版**（プロジェクト標準）:
```javascript
/**
 * トースト通知を表示
 * @param {string} toastId - トーストのID（#successToast, #errorToast等）
 * @param {string} message - 表示するメッセージ
 * @param {number} delay - 自動非表示までの時間（ミリ秒、デフォルト5000）
 */
function showToast(toastId, message, delay = 5000) {
  const $toast = $(toastId);

  // メッセージを更新
  $toast.find('.toast-body').text(message);

  // Bootstrapトーストインスタンスを取得または作成
  const toastEl = $toast[0];
  const toast = bootstrap.Toast.getOrCreateInstance(toastEl, {
    autohide: true,
    delay: delay
  });

  // 表示
  toast.show();
}

// 使用例
showToast('#successToast', 'マッピングを追加しました');
showToast('#errorToast', 'CSVファイルの形式が不正です');
showToast('#warningToast', '未登録店舗が3件あります', 7000); // 7秒表示
showToast('#infoToast', 'スプレッドシートIDを更新しました');
```

**Vanilla JS版**（参考）:
```javascript
/**
 * トースト通知を表示（Vanilla JS版）
 * @param {string} selector - トーストのセレクタ
 * @param {string} message - 表示するメッセージ
 * @param {number} delay - 自動非表示までの時間（ミリ秒）
 */
function showToastVanilla(selector, message, delay = 5000) {
  const toastEl = document.querySelector(selector);

  // メッセージを更新
  toastEl.querySelector('.toast-body').textContent = message;

  // Bootstrapトーストインスタンスを取得または作成
  const toast = bootstrap.Toast.getOrCreateInstance(toastEl, {
    autohide: true,
    delay: delay
  });

  // 表示
  toast.show();
}

// 使用例
showToastVanilla('#successToast', 'マッピングを追加しました');
```

#### 重要な注意事項

1. **複数トーストの重ね表示**:
   - Bootstrap 5.3は複数トーストを縦に積み重ねて表示可能
   - ARIA衝突を避けるため、各トーストに固有のIDを付与
   - 同時に3件以上表示する場合は、古いトーストを自動的に閉じることを検討

2. **長文メッセージの対応**:
   - デフォルトの`max-width`は`350px`
   - 長文の場合は`max-width: min(320px, 90vw)`を適用してモバイル対応
   - 詳細メッセージが必要な場合はモーダルダイアログを使用

3. **トースト内のインタラクション**:
   - トーストにリンクやボタンを含める場合、`autohide: false`に設定
   - キーボードユーザーが操作できるよう、フォーカス管理を実装

4. **Z-index管理**:
   - Bootstrap 5.3のトーストはデフォルトで`z-index: 1090`
   - モーダル（`z-index: 1055`）より前面に表示される
   - カスタムCSSで調整が必要な場合は`config.py`で定義

#### アクセシビリティ考慮事項

1. **スクリーンリーダー対応**:
   - `role="alert"`: 重要な通知として即座にアナウンス
   - `aria-live="assertive"`: 現在の読み上げを中断して優先通知
   - `aria-atomic="true"`: メッセージ全体を一度に読み上げ

2. **キーボード操作**:
   - トースト内の閉じるボタン（`.btn-close`）はTabキーでフォーカス可能
   - `aria-label="閉じる"`で目的を明示
   - トースト自体はフォーカス不可（静的情報）

3. **視覚的配慮**:
   - 色だけでなくアイコンとテキストで状態を伝達
   - 成功（緑）、エラー（赤）、警告（黄）、情報（青）のコントラスト比をWCAG AA基準で確保
   - アニメーションは`prefers-reduced-motion`メディアクエリに対応（Bootstrap 5.3デフォルト）

---

### 3. モーダルダイアログ（確認・エラー詳細）

#### 目的
- 破壊的操作（マッピング削除、未登録店舗一括追加）の確認ダイアログ
- 詳細エラーメッセージの表示（トーストでは収まらない長文）
- ユーザーに再確認を促し、誤操作を防止

#### UI仕様

**使用コンポーネント**: Bootstrap 5.3 `.modal`

- **サイズ**: デフォルト（500px）、必要に応じて`.modal-lg`（800px）使用
- **配置**: `.modal-dialog-centered`で垂直中央配置
- **アニメーション**: `.fade`クラスでフェードイン/アウト
- **背景**: 半透明黒背景（`.modal-backdrop`）、クリックで閉じる挙動は用途により設定

#### 主要モーダルID定義

| モーダルID | 用途 | 画面 | ボタン種類 |
|-----------|------|------|-----------|
| `#deleteConfirmModal` | マッピング削除確認 | mapping.html | キャンセル（secondary）、削除（danger） |
| `#bulkAddModal` | 未登録店舗一括追加確認 | index.html | キャンセル（secondary）、追加（primary） |
| `#errorDetailModal` | エラー詳細表示 | 全画面 | 閉じる（secondary） |

#### HTML構造例（削除確認モーダル）

```html
{% block modals %}

<!-- マッピング削除確認モーダル -->
<div class="modal fade" id="deleteConfirmModal" tabindex="-1"
     aria-labelledby="deleteModalLabel" aria-modal="true" role="dialog">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">

      <!-- ヘッダー -->
      <div class="modal-header">
        <h5 class="modal-title" id="deleteModalLabel">削除確認</h5>
        <button type="button" class="btn-close"
                data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>

      <!-- ボディ -->
      <div class="modal-body">
        <p>このマッピングを削除してもよろしいですか？</p>
        <p class="text-muted mb-0">
          店舗名: <span id="deleteStoreName" class="fw-bold"></span>
        </p>
      </div>

      <!-- フッター -->
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary"
                data-bs-dismiss="modal">キャンセル</button>
        <button type="button" class="btn btn-danger"
                id="confirmDeleteBtn">削除</button>
      </div>

    </div>
  </div>
</div>

<!-- 一括追加確認モーダル -->
<div class="modal fade" id="bulkAddModal" tabindex="-1"
     aria-labelledby="bulkAddModalLabel" aria-modal="true" role="dialog">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="bulkAddModalLabel">一括追加確認</h5>
        <button type="button" class="btn-close"
                data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>
      <div class="modal-body">
        <p><span id="bulkAddCount" class="fw-bold"></span>件の未登録店舗をデフォルト列（B列）に振り分けます。</p>
        <p class="text-muted mb-0">この操作は元に戻せません。</p>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary"
                data-bs-dismiss="modal">キャンセル</button>
        <button type="button" class="btn btn-primary"
                id="confirmBulkAddBtn">追加</button>
      </div>
    </div>
  </div>
</div>

<!-- エラー詳細モーダル -->
<div class="modal fade" id="errorDetailModal" tabindex="-1"
     aria-labelledby="errorDetailModalLabel" aria-modal="true" role="dialog">
  <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header bg-danger text-white">
        <h5 class="modal-title" id="errorDetailModalLabel">エラー詳細</h5>
        <button type="button" class="btn-close btn-close-white"
                data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>
      <div class="modal-body">
        <pre id="errorDetailContent" class="mb-0"></pre>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary"
                data-bs-dismiss="modal">閉じる</button>
      </div>
    </div>
  </div>
</div>

{% endblock %}
```

**HTML構造のポイント**:
- `tabindex="-1"`: モーダル全体をフォーカス可能にする（Bootstrap必須）
- `aria-labelledby`: モーダルタイトルとの紐付け（アクセシビリティ）
- `aria-modal="true"`: モーダルダイアログであることを明示
- `role="dialog"`: ダイアログの役割を定義
- `.modal-dialog-centered`: 垂直中央配置
- `.modal-dialog-scrollable`: 長文用スクロール対応（エラー詳細）
- `.btn-close-white`: 暗背景（`.bg-danger`）用の白い閉じるボタン

#### JavaScript制御例

**jQuery版**（プロジェクト標準）:
```javascript
/**
 * 削除確認モーダルを表示
 * @param {string} storeName - 店舗名
 * @param {number} mappingId - マッピングID
 */
function openDeleteModal(storeName, mappingId) {
  // 店舗名を表示
  $('#deleteStoreName').text(storeName).data('mapping-id', mappingId);

  // モーダルインスタンスを作成して表示
  const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
  modal.show();
}

// 削除ボタンクリックハンドラ
$('#confirmDeleteBtn').on('click', function() {
  const mappingId = $('#deleteStoreName').data('mapping-id');

  // 削除API呼び出し
  $.ajax({
    url: `/mapping/delete/${mappingId}`,
    method: 'DELETE',
    headers: { 'X-CSRFToken': csrfToken }
  })
  .done(function(response) {
    // モーダルを閉じる
    bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal')).hide();

    // 成功トースト表示
    showToast('#successToast', 'マッピングを削除しました');

    // マッピング一覧を再読込
    loadMappingList();
  })
  .fail(function(error) {
    // エラートースト表示
    showToast('#errorToast', '削除に失敗しました');
  });
});

/**
 * 一括追加確認モーダルを表示
 * @param {number} count - 未登録店舗数
 */
function openBulkAddModal(count) {
  $('#bulkAddCount').text(count);

  const modal = new bootstrap.Modal(document.getElementById('bulkAddModal'));
  modal.show();
}

/**
 * エラー詳細モーダルを表示
 * @param {string} errorMessage - エラーメッセージ（JSON等）
 */
function openErrorDetailModal(errorMessage) {
  $('#errorDetailContent').text(errorMessage);

  const modal = new bootstrap.Modal(document.getElementById('errorDetailModal'));
  modal.show();
}
```

**Vanilla JS版**（参考）:
```javascript
// 削除確認モーダル表示
const deleteModalEl = document.getElementById('deleteConfirmModal');
const deleteModal = new bootstrap.Modal(deleteModalEl);

function openDeleteModalVanilla(storeName, mappingId) {
  document.getElementById('deleteStoreName').textContent = storeName;
  deleteModalEl.dataset.mappingId = mappingId;
  deleteModal.show();
}

// 削除ボタンクリック
document.getElementById('confirmDeleteBtn').addEventListener('click', async function() {
  const mappingId = deleteModalEl.dataset.mappingId;

  try {
    const response = await fetch(`/mapping/delete/${mappingId}`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': csrfToken }
    });

    if (response.ok) {
      deleteModal.hide();
      showToastVanilla('#successToast', 'マッピングを削除しました');
      loadMappingList();
    } else {
      throw new Error('削除失敗');
    }
  } catch (error) {
    showToastVanilla('#errorToast', '削除に失敗しました');
  }
});
```

#### 重要な注意事項

1. **モーダルの連鎖禁止**:
   - 同時に複数のモーダルを表示しない（Bootstrap制約）
   - モーダルを閉じてから別のモーダルを開く
   - エラーモーダル表示前に確認モーダルを閉じる

2. **背景スクロール制御**:
   - モーダル表示中は背景スクロールを自動的に無効化（Bootstrap デフォルト）
   - `backdrop: 'static'`オプションで背景クリック無効化（破壊的操作に推奨）

3. **長文コンテンツの対応**:
   - `.modal-dialog-scrollable`を使用してモーダル内スクロール
   - エラー詳細やログ表示に適用
   - `<pre>`タグでフォーマット済みテキストを表示

4. **フォーカス管理**:
   - モーダル表示時、最初のフォーカス可能要素に自動フォーカス
   - モーダルを閉じたら、元のトリガー要素にフォーカスを戻す（Bootstrap自動処理）

#### アクセシビリティ考慮事項

1. **スクリーンリーダー対応**:
   - `aria-modal="true"`: モーダルダイアログであることを明示
   - `aria-labelledby`: タイトル（`.modal-title`）とモーダルを紐付け
   - `aria-describedby`: 説明文（`.modal-body`）との紐付け（オプション）

2. **キーボード操作**:
   - **Tabキー**: モーダル内の要素間を循環（外部要素にフォーカス不可）
   - **Escキー**: モーダルを閉じる（デフォルト動作、`keyboard: true`）
   - **Enterキー**: プライマリボタン（削除/追加）を実行（カスタム実装）

3. **フォーカストラップ**:
   - モーダル表示中は背景要素にフォーカス不可（Bootstrap自動実装）
   - モーダルを閉じたら元のトリガー要素にフォーカスを戻す

4. **視覚的配慮**:
   - 破壊的操作（削除）は`.btn-danger`で赤色表示
   - エラーモーダルのヘッダーは`.bg-danger.text-white`で視認性向上
   - モーダル背景（`.modal-backdrop`）の透明度はデフォルトで適切

---

### H-3対応の実装チェックリスト（Step 3.1）

以下の項目をStep 3.1実装時に確認してください：

#### プログレスインジケーター
- [ ] `base.html`に`{% block progress %}`が定義されている
- [ ] プログレスインジケーターが`<main>`タグの直前に配置されている
- [ ] `.spinner-border.spinner-border-sm`が使用されている
- [ ] `role="status"`と`aria-live="polite"`が設定されている
- [ ] デフォルトで`.d-none`クラスで非表示になっている
- [ ] ブラウザConsoleで`$('#progressIndicator').toggleClass('d-none')`動作確認完了

#### トースト通知
- [ ] `base.html`に`.toast-container.position-fixed.top-0.end-0.p-3`が配置されている
- [ ] 4種類のトースト（成功/エラー/警告/情報）が実装されている
- [ ] 各トーストに`role="alert"`, `aria-live="assertive"`, `aria-atomic="true"`が設定されている
- [ ] `.btn-close`ボタンに`aria-label="閉じる"`が設定されている
- [ ] `showToast()`関数が実装されている
- [ ] ブラウザConsoleで`showToast('#successToast', 'テスト')`動作確認完了

#### モーダルダイアログ
- [ ] `base.html`に`{% block modals %}`が定義されている
- [ ] `#deleteConfirmModal`, `#bulkAddModal`, `#errorDetailModal`が実装されている
- [ ] 各モーダルに`tabindex="-1"`, `aria-labelledby`, `aria-modal="true"`, `role="dialog"`が設定されている
- [ ] `.modal-dialog-centered`で中央配置されている
- [ ] エラー詳細モーダルに`.modal-dialog-scrollable`が設定されている
- [ ] ブラウザConsoleで`new bootstrap.Modal(document.getElementById('deleteConfirmModal')).show()`動作確認完了

#### Bootstrap 5.3準拠
- [ ] 全コンポーネントがBootstrap 5.3公式仕様に準拠している
- [ ] カスタムCSSでBootstrapクラスを上書きしていない
- [ ] アクセシビリティ属性（ARIA）が正しく設定されている

---

## H-4対応: ロールバック手順書とGit運用規約

### Git運用フロー

**Phase単位でのコミット戦略**:

```
Phase 3 Step 3.1: ベーステンプレート作成
    ↓
  [実装]
    ↓
  [動作確認]
    ↓
  [コミット: feature/step-3-1-base-template]
    ↓
  [タグ付け: phase3-step1]
    ↓
  [メインブランチにマージ]
```

### コミットメッセージ規約

**フォーマット**:
```
<Type>(<Scope>): <Subject>

<Body>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Type一覧**:
- `feat`: 新機能追加
- `fix`: バグ修正
- `refactor`: リファクタリング
- `docs`: ドキュメント更新
- `test`: テスト追加・修正
- `chore`: 環境設定・ビルド関連

**Scope例**:
- `frontend`: フロントエンド関連
- `backend`: バックエンド関連
- `docker`: Docker設定
- `security`: セキュリティ対応

**Subject**:
- 50文字以内
- 命令形（"Add", "Fix", "Update"）
- 日本語可（"追加", "修正", "更新"）

**例**:
```
feat(frontend): Step 3.1 ベーステンプレート実装

- templates/base.html作成（Bootstrap 5.3, jQuery 3.7+）
- セキュリティヘッダー設定（CSP, Referrer-Policy等）
- X-XSS-Protection削除（非推奨ヘッダー）
- ナビゲーションバー実装（メイン/マッピング管理）

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### タグ付けルール

**タグ命名規則**:
```
phase<Phase番号>-step<Step番号>
```

**例**:
- `phase3-step1`: Phase 3 Step 3.1完了
- `phase3-step2`: Phase 3 Step 3.2完了

**タグ作成コマンド**:
```bash
# アノテーション付きタグ（推奨）
git tag -a phase3-step1 -m "Phase 3 Step 3.1: ベーステンプレート実装完了"

# タグをリモートにプッシュ
git push origin phase3-step1
```

### ロールバック手順書

#### シナリオ1: テンプレート破損時の復旧

**発生条件**:
- Step 3.2でbase.htmlを破壊的に編集してしまった
- Step 3.1の状態に戻したい

**復旧手順**:

```bash
# 1. 現在の変更を一時退避（必要に応じて）
git stash

# 2. Step 3.1のタグにチェックアウト
git checkout tags/phase3-step1

# 3. 特定ファイルを復元（base.htmlのみ）
git checkout tags/phase3-step1 -- templates/base.html

# 4. 現在のブランチに戻る
git checkout feature/step-3-2-main-page

# 5. 変更を確認
git status

# 6. コミット
git add templates/base.html
git commit -m "fix(frontend): base.htmlをphase3-step1の状態に復元"
```

#### シナリオ2: Phase全体のロールバック

**発生条件**:
- Phase 3の実装が失敗、Phase 2の状態に戻したい

**復旧手順（ローカル開発）**:

```bash
# 1. Phase 2のタグを確認
git tag -l "phase2*"
# → phase2-step5（最終ステップ）

# 2. タグにチェックアウト
git checkout tags/phase2-step5

# 3. 新しいブランチを作成
git checkout -b feature/phase3-retry

# 4. Phase 3を再実装
# ...
```

**復旧手順（Docker環境）**:

```bash
# 1. コンテナ停止
docker-compose down

# 2. Gitロールバック
git checkout tags/phase2-step5

# 3. Dockerイメージ再ビルド
docker-compose build --no-cache

# 4. コンテナ起動
docker-compose up -d

# 5. 動作確認
curl -f http://localhost:5000/
```

#### シナリオ3: 本番環境での緊急ロールバック

**発生条件**:
- Phase 3デプロイ後、致命的なバグ発見
- 即座にPhase 2に戻す必要がある

**復旧手順**:

```bash
# 1. 現在のバージョンを確認
git describe --tags
# → phase3-step2-5-g1a2b3c4

# 2. Phase 2のタグにハードリセット（本番環境のみ）
git reset --hard tags/phase2-step5

# 3. リモートに強制プッシュ（注意: 慎重に実行）
git push origin main --force-with-lease

# 4. Docker環境の再デプロイ
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 5. ヘルスチェック
docker-compose ps
curl -f http://localhost:5000/

# 6. ログ確認
docker-compose logs -f --tail=100
```

### Phase Exit チェックリスト

**各Phaseステップ完了時に実施**:

- [ ] 実装コードのレビュー（PEP 8準拠確認）
- [ ] 動作確認（ブラウザ/Playwright MCP）
- [ ] Gitステータス確認（`git status`）
- [ ] Gitコミット（コミットメッセージ規約準拠）
- [ ] Gitタグ作成（`git tag -a phase<X>-step<Y>`）
- [ ] リモートプッシュ（`git push origin <branch>` + `git push origin <tag>`）
- [ ] ロールバックポイント記録（README更新）

### 緊急時の連絡体制（個人開発のため省略可）

- **緊急連絡先**: N/A（個人開発プロジェクト）
- **エスカレーション**: N/A
- **復旧SLA**: ベストエフォート

---

## 修正版 requirements.txt

**Step 3.1版（Flask-WTF削除）**:

```txt
Flask==3.1.2
pandas==2.2.0
google-api-python-client==2.140.0
google-auth==2.23.4
gspread==6.0.0
gunicorn==23.0.0
chardet==5.2.0
pytest==9.0.1
pytest-cov==7.0.0
```

**変更内容**:
- Flask-WTF削除（Step 3.2以降で追加予定）
- python-dotenv削除（Docker環境では不要）

**Step 3.2以降での追加予定**:
```txt
Flask-WTF==1.2.1  # CSRF保護・フォーム検証
python-dotenv==1.0.0  # ローカルCLI開発用（オプション）
```

---

## 修正版セキュリティヘッダー設定（実装例）

**ファイル**: `app.py`
**実装箇所**: `@app.after_request`デコレータ

```python
@app.after_request
def set_security_headers(response):
    """
    セキュリティヘッダーを設定

    OWASP推奨のセキュリティヘッダーを全レスポンスに追加。
    - CSP（Content-Security-Policy）: XSS対策
    - X-Content-Type-Options: MIMEスニッフィング防止
    - X-Frame-Options: クリックジャッキング防止
    - Referrer-Policy: リファラー制御
    - Permissions-Policy: 不要な機能無効化
    - HSTS（本番のみ）: HTTPS強制

    注意:
    - X-XSS-Protectionは非推奨のため使用しない
    - CSPは開発/本番で設定を切り替え

    Args:
        response (Response): Flaskレスポンスオブジェクト

    Returns:
        Response: ヘッダー追加後のレスポンス
    """
    # CSP設定（環境別）
    if app.config['DEBUG']:
        # 開発環境: Bootstrap/jQuery CDN許可、unsafe-inline許可
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://code.jquery.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self' https://accounts.google.com https://sheets.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'"
        )
    else:
        # 本番環境: 厳格設定（unsafe-inline削除、upgrade-insecure-requests追加）
        csp = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self' https://accounts.google.com https://sheets.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'; "
            "upgrade-insecure-requests"
        )

    response.headers['Content-Security-Policy'] = csp

    # XSS対策（CSPで対応、X-XSS-Protectionは非推奨）
    # response.headers['X-XSS-Protection'] = '...'  # 削除

    # MIMEスニッフィング防止
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # クリックジャッキング防止
    response.headers['X-Frame-Options'] = 'DENY'

    # リファラー制御
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # 不要な機能の無効化
    response.headers['Permissions-Policy'] = 'camera=(), geolocation=(), microphone=()'

    # HSTS（本番環境のみ、HTTPS必須）
    if not app.config['DEBUG']:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response
```

**動作確認コマンド**:
```bash
# ヘッダーの確認
curl -I http://localhost:5000/

# 期待される出力
HTTP/1.1 200 OK
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' ...
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), geolocation=(), microphone=()
```

---

## base.html設計（修正版：UI共通コンポーネント統合）

### HTML構造の全体像

以下は、H-3対応（UI共通コンポーネント）を統合した`templates/base.html`の完全な設計です。

```html
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}イオンカード明細取込システム{% endblock %}</title>

  <!-- Bootstrap 5.3 CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        rel="stylesheet"
        integrity="sha384-9ndCyUaIbzAi2FUVXJi0CjmCapSmO7SnpJef0486qhLnuZ2cdeRhO02iuK6FUUVM"
        crossorigin="anonymous">

  <!-- Bootstrap Icons (オプション) -->
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.min.css"
        integrity="sha384-4LISF5TTJX/fLmGSxO53rV4miRxdg84mZsxmO8Rx5jGtp/LbrixFETvWa5a6sESd"
        crossorigin="anonymous">

  <!-- カスタムCSS（将来的に追加） -->
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">

  {% block head_extra %}{% endblock %}
</head>
<body>

  <!-- ナビゲーションバー -->
  <nav class="navbar navbar-expand-lg navbar-dark bg-primary sticky-top">
    <div class="container-fluid">
      <!-- ブランドロゴ -->
      <a class="navbar-brand" href="{{ url_for('index') }}">
        <i class="bi bi-credit-card"></i> Credit Detail
      </a>

      <!-- モバイルハンバーガーメニュー -->
      <button class="navbar-toggler" type="button"
              data-bs-toggle="collapse"
              data-bs-target="#mainNav"
              aria-controls="mainNav"
              aria-expanded="false"
              aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>

      <!-- ナビゲーションメニュー -->
      <div class="collapse navbar-collapse" id="mainNav">
        <ul class="navbar-nav me-auto">
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('index') }}">
              <i class="bi bi-house"></i> ホーム
            </a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('mapping') }}">
              <i class="bi bi-list-ul"></i> マッピング管理
            </a>
          </li>
        </ul>
      </div>
    </div>
  </nav>

  <!-- プログレスインジケーター領域 -->
  {% block progress %}
  <div id="progressIndicator" class="alert alert-info d-none" role="status" aria-live="polite">
    <div class="d-flex align-items-center">
      <div class="spinner-border spinner-border-sm text-primary me-2" aria-hidden="true"></div>
      <span>処理中…しばらくお待ちください。</span>
    </div>
  </div>
  {% endblock %}

  <!-- メインコンテンツ -->
  <main class="container py-4">
    {% block content %}{% endblock %}
  </main>

  <!-- トースト通知領域（position: fixed） -->
  <div class="toast-container position-fixed top-0 end-0 p-3" aria-live="polite" aria-atomic="true">
    {% block toasts %}
    <!-- 成功トースト -->
    <div id="successToast" class="toast align-items-center text-bg-success border-0"
         role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">処理が完了しました。</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast" aria-label="閉じる"></button>
      </div>
    </div>

    <!-- エラートースト -->
    <div id="errorToast" class="toast align-items-center text-bg-danger border-0"
         role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">エラーが発生しました。</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast" aria-label="閉じる"></button>
      </div>
    </div>

    <!-- 警告トースト -->
    <div id="warningToast" class="toast align-items-center text-bg-warning border-0"
         role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">未登録店舗が検出されました。</div>
        <button type="button" class="btn-close me-2 m-auto"
                data-bs-dismiss="toast" aria-label="閉じる"></button>
      </div>
    </div>

    <!-- 情報トースト -->
    <div id="infoToast" class="toast align-items-center text-bg-info border-0"
         role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">設定が更新されました。</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast" aria-label="閉じる"></button>
      </div>
    </div>
    {% endblock %}
  </div>

  <!-- モーダルダイアログ領域 -->
  {% block modals %}
  <!-- マッピング削除確認モーダル -->
  <div class="modal fade" id="deleteConfirmModal" tabindex="-1"
       aria-labelledby="deleteModalLabel" aria-modal="true" role="dialog">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="deleteModalLabel">削除確認</h5>
          <button type="button" class="btn-close"
                  data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <p>このマッピングを削除してもよろしいですか？</p>
          <p class="text-muted mb-0">
            店舗名: <span id="deleteStoreName" class="fw-bold"></span>
          </p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary"
                  data-bs-dismiss="modal">キャンセル</button>
          <button type="button" class="btn btn-danger"
                  id="confirmDeleteBtn">削除</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 一括追加確認モーダル -->
  <div class="modal fade" id="bulkAddModal" tabindex="-1"
       aria-labelledby="bulkAddModalLabel" aria-modal="true" role="dialog">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="bulkAddModalLabel">一括追加確認</h5>
          <button type="button" class="btn-close"
                  data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <p><span id="bulkAddCount" class="fw-bold"></span>件の未登録店舗をデフォルト列（B列）に振り分けます。</p>
          <p class="text-muted mb-0">この操作は元に戻せません。</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary"
                  data-bs-dismiss="modal">キャンセル</button>
          <button type="button" class="btn btn-primary"
                  id="confirmBulkAddBtn">追加</button>
        </div>
      </div>
    </div>
  </div>

  <!-- エラー詳細モーダル -->
  <div class="modal fade" id="errorDetailModal" tabindex="-1"
       aria-labelledby="errorDetailModalLabel" aria-modal="true" role="dialog">
    <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content">
        <div class="modal-header bg-danger text-white">
          <h5 class="modal-title" id="errorDetailModalLabel">エラー詳細</h5>
          <button type="button" class="btn-close btn-close-white"
                  data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <pre id="errorDetailContent" class="mb-0"></pre>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary"
                  data-bs-dismiss="modal">閉じる</button>
        </div>
      </div>
    </div>
  </div>
  {% endblock %}

  <!-- フッター -->
  <footer class="text-center text-muted py-4 mt-5 border-top">
    {% block footer %}
    <p class="mb-0">&copy; 2025 イオンカード明細取込システム</p>
    {% endblock %}
  </footer>

  <!-- Bootstrap 5.3 JavaScript Bundle -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
          integrity="sha384-geWF76RCwLtnZ8qwWowPQNguL3RmwHVBC9FhGdlKrxdiJJigb/j/68SIy3Te4Bkz"
          crossorigin="anonymous"></script>

  <!-- jQuery 3.7+ -->
  <script src="https://code.jquery.com/jquery-3.7.1.min.js"
          integrity="sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo="
          crossorigin="anonymous"></script>

  <!-- カスタムJavaScript -->
  {% block scripts %}{% endblock %}

</body>
</html>
```

### 設計のポイント

#### 1. UI共通コンポーネントの配置順序

```
<body>
  <nav>        <!-- ナビゲーションバー -->
    ↓
  {% block progress %}  <!-- プログレスインジケーター（<main>直前） -->
    ↓
  <main>       <!-- メインコンテンツ -->
    ↓
  <div.toast-container>  <!-- トースト通知（position: fixed） -->
    ↓
  {% block modals %}  <!-- モーダルダイアログ（<body>末尾近く） -->
    ↓
  <footer>     <!-- フッター -->
    ↓
  <script>     <!-- JavaScript読み込み -->
</body>
```

**理由**:
- **プログレスインジケーター**: `<main>`直前に配置し、コンテンツの上部に表示
- **トースト通知**: `position: fixed`で画面右上に固定、DOM上の位置は任意だがbody直下を推奨
- **モーダルダイアログ**: `<body>`末尾に配置してz-index管理を簡素化、フッターより前

#### 2. Jinja2ブロック定義

| ブロック名 | 用途 | デフォルト実装 |
|-----------|------|--------------|
| `{% block title %}` | ページタイトル | 「イオンカード明細取込システム」 |
| `{% block head_extra %}` | 追加CSSやMeta | 空 |
| `{% block progress %}` | プログレスインジケーター | デフォルトスピナー実装 |
| `{% block content %}` | メインコンテンツ | 空（各ページで実装） |
| `{% block toasts %}` | トースト通知 | 4種類のトースト実装 |
| `{% block modals %}` | モーダルダイアログ | 3種類のモーダル実装 |
| `{% block footer %}` | フッター | デフォルト著作権表示 |
| `{% block scripts %}` | カスタムJavaScript | 空 |

#### 3. Bootstrap 5.3 CDN読み込み

**CSS**:
- URL: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css`
- Integrity: SHA384ハッシュで改ざん検証
- Crossorigin: `anonymous`で CORS 対応

**JavaScript**:
- URL: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js`
- Bundle版: Popper.js含む（モーダル・トースト・ドロップダウンに必須）
- Integrity: SHA384ハッシュで改ざん検証

**jQuery**:
- バージョン: 3.7.1（最新安定版）
- URL: `https://code.jquery.com/jquery-3.7.1.min.js`
- Integrity: SHA256ハッシュで改ざん検証

#### 4. CSP（Content-Security-Policy）対応

**開発環境**:
- `script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com`
- `style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net`

**本番環境（将来的）**:
- `'unsafe-inline'`を削除し、nonce方式に移行
- app.pyの`@app.after_request`でnonce生成
- `<script nonce="{{ nonce }}">`形式で適用

#### 5. アクセシビリティ配慮

- **ARIA属性の適切な使用**:
  - プログレスインジケーター: `role="status"`, `aria-live="polite"`
  - トースト: `role="alert"`, `aria-live="assertive"`, `aria-atomic="true"`
  - モーダル: `aria-modal="true"`, `aria-labelledby`, `role="dialog"`

- **キーボードナビゲーション**:
  - ナビゲーションバー: Tabキーで各リンクにフォーカス可能
  - モーダル: Tabキーで内部要素を循環、Escキーで閉じる
  - トースト: 閉じるボタンにフォーカス可能

- **視覚的フィードバック**:
  - 色だけでなくアイコン（Bootstrap Icons）でも情報伝達
  - コントラスト比をWCAG AA基準で確保

#### 6. レスポンシブデザイン

- **ナビゲーションバー**: `.navbar-expand-lg`でモバイル時にハンバーガーメニュー
- **コンテナ**: `.container`で最大幅を自動調整（576px/768px/992px/1200px/1400px）
- **トースト**: `max-width: min(320px, 90vw)`でモバイル対応（CSS追加）
- **モーダル**: `.modal-dialog`がデフォルトでレスポンシブ

---

## Step 3.1実装スコープ（修正版）

### 実装対象

**1. ベーステンプレート（templates/base.html）**:
- [ ] HTML5基本構造
- [ ] Bootstrap 5.3 CDN読込
- [ ] jQuery 3.7+ CDN読込
- [ ] ナビゲーションバー（メイン/マッピング管理リンク）
  - [ ] **ルート名チェック**: `url_for('index')`使用（❌ `url_for('index_page')`ではない）
  - [ ] **ルート名チェック**: `url_for('mapping')`使用（❌ `url_for('mapping_page')`ではない）
  - [ ] `/result`はナビゲーションに含めない（処理後遷移先のため）
- [ ] フッター
- [ ] コンテンツブロック定義（`{% block content %}`）
- [ ] スクリプトブロック定義（`{% block scripts %}`）
- [ ] **UI共通コンポーネント領域**:
  - [ ] プログレスインジケーター用`{% block progress %}`
  - [ ] トースト通知用`.toast-container`（position: fixed）
  - [ ] モーダルダイアログ用`{% block modals %}`

**2. セキュリティヘッダー設定（app.py）**:
- [ ] `@app.after_request`デコレータ追加
- [ ] CSP設定（開発/本番環境切り替え）
- [ ] X-Content-Type-Options設定
- [ ] X-Frame-Options設定
- [ ] Referrer-Policy設定
- [ ] Permissions-Policy設定
- [ ] HSTS設定（本番のみ）

**3. 動作確認**:
- [ ] Dockerコンテナ再ビルド（`docker-compose build`）
- [ ] コンテナ起動（`docker-compose up -d`）
- [ ] ブラウザアクセス（http://localhost:5000）
- [ ] ナビゲーション動作確認
  - [ ] **ルート名検証**: 「ホーム」リンクが`/`に遷移（`url_for('index')`）
  - [ ] **ルート名検証**: 「マッピング管理」リンクが`/mapping`に遷移（`url_for('mapping')`）
  - [ ] ブランドロゴクリックで`/`に遷移（`url_for('index')`）
- [ ] セキュリティヘッダー確認（`curl -I`）
- [ ] ChromeデベロッパーツールでCSP警告確認
- [ ] **UI共通コンポーネント動作確認**（ブラウザConsole）:
  - [ ] プログレスインジケーター: `$('#progressIndicator').toggleClass('d-none')`
  - [ ] トースト通知: `showToast('#successToast', 'テスト')`
  - [ ] モーダルダイアログ: `new bootstrap.Modal(document.getElementById('deleteConfirmModal')).show()`

**4. Git運用**:
- [ ] 実装コミット（`git add` + `git commit`）
- [ ] タグ作成（`git tag -a phase3-step1`）
- [ ] リモートプッシュ（`git push origin <branch> <tag>`）

### 実装対象外（Step 3.2以降に延期）

**Flask-WTF関連**:
- ❌ Flask-WTF導入（requirements.txtへの追加）
- ❌ CSRFProtect初期化
- ❌ `<meta name="csrf-token">`追加
- ❌ フォームクラス定義（WTForms）

**JavaScript実装**:
- ❌ csrfFetch()関数実装
- ❌ main.js詳細実装
- ❌ mapping.js実装

**ページテンプレート**:
- ❌ index.html詳細実装（Step 3.2）
- ❌ mapping.html詳細実装（Step 3.3）
- ❌ result.html詳細実装（Step 3.4）

---

## 影響範囲の説明

### C-1修正の影響

**影響を受けるもの**:
- templates/base.htmlのナビゲーションバー実装
- すべてのテンプレートファイルでの`url_for()`使用方法
- JavaScript内でのURL生成（Jinja2経由）

**影響を受けないもの**:
- app.pyのルート定義（変更なし、確認のみ）
- バックエンドAPIロジック
- Dockerコンテナ構成

**リスク軽減**:
- 実装前にルート名一覧を確認
- 実装後にリンク動作を全数検証
- 誤ったルート名の禁止リストを作成

### C-2修正の影響

**影響を受けるもの**:
- Step 3.1のタスクリスト（Flask-WTF関連タスク削除）
- requirements.txt（Flask-WTF削除）
- 実装スケジュール（Step 3.2にCSRF実装を集約）

**影響を受けないもの**:
- 既存のバックエンドAPI（Phase 2実装済み）
- Dockerコンテナ構成
- Google Sheets連携機能

### C-3修正の影響

**新規作成が必要なもの**:
- CSRF実装設計書（本ドキュメントに含む）
- csrfFetch() JavaScriptヘルパー関数（Step 3.2）
- @app.context_processor実装（Step 3.2）

**既存コードへの影響**:
- なし（Step 3.2以降で段階的に実装）

### H-1修正の影響

**変更が必要なもの**:
- なし（現状のapp.pyとconfig.pyは環境変数ベース）
- python-dotenvはオプション扱い（ローカルCLI開発時のみ）

**明確化されたこと**:
- Docker環境ではpython-dotenv不要
- 12-Factor App準拠の確認

### H-2修正の影響

**変更が必要なもの**:
- app.pyの`@app.after_request`実装（新規追加）
- X-XSS-Protectionの削除（該当コードなし、今後も使用しない）

**影響範囲**:
- 全HTTPレスポンスヘッダー（セキュリティ向上）

### H-4修正の影響

**新規作成が必要なもの**:
- コミットメッセージ規約（本ドキュメントに含む）
- タグ付けルール（本ドキュメントに含む）
- ロールバック手順書（本ドキュメントに含む）

**開発フローへの影響**:
- 各Phaseステップ完了時にタグ作成が必須化
- コミット前のチェックリスト実施

---

## 次のステップ

### Step 3.1実装（本ドキュメント完成後）

1. **ベーステンプレート作成**:
   - `templates/base.html`実装
   - Bootstrap 5.3、jQuery 3.7+統合
   - ナビゲーションバー実装

2. **セキュリティヘッダー設定**:
   - `app.py`に`@app.after_request`追加
   - CSP、Referrer-Policy等設定

3. **動作確認**:
   - Docker再ビルド・起動
   - ブラウザアクセステスト
   - セキュリティヘッダー確認

4. **Git運用**:
   - コミット作成
   - タグ付け（`phase3-step1`）
   - リモートプッシュ

### Step 3.2実装（次回）

1. **Flask-WTF導入**:
   - requirements.txt更新
   - CSRFProtect初期化

2. **CSRF実装**:
   - Meta+Fetchヘッダー方式実装
   - csrfFetch()関数実装
   - 既存のfetch()置き換え

3. **メイン画面実装**:
   - `templates/index.html`詳細実装
   - `static/js/main.js`実装

---

## まとめ

### 修正完了項目

| ID | 問題 | 修正内容 | ステータス |
|----|------|---------|-----------|
| C-1 | ルート名の不整合 | url_for()の正確なルート名を明記、実装チェックリスト追加 | ✅ 完了 |
| C-2 | Flask-WTF導入タイミング | Step 3.2以降に延期 | ✅ 完了 |
| C-3 | CSRF実装方法 | Meta+Fetchヘッダー方式採用、設計書作成 | ✅ 完了 |
| H-1 | python-dotenv二重管理 | Docker環境では不要と明確化 | ✅ 完了 |
| H-2 | セキュリティヘッダー非推奨 | CSP等現代的ヘッダーに更新 | ✅ 完了 |
| **H-3** | **UI共通コンポーネント未設計** | **プログレス/トースト/モーダルの詳細仕様を追加** | ✅ **完了** |
| H-4 | Git運用手順未策定 | Git運用規約・ロールバック手順書作成 | ✅ 完了 |

### Step 3.1実装準備完了

- ✅ 修正版実装計画書作成
- ✅ ルート名の不整合修正（C-1対応）
  - ✅ app.py実際のルート関数名の明記
  - ✅ 正しい`url_for()`の使い方を明示
  - ✅ 誤ったルート名の禁止事項リスト作成
  - ✅ ナビゲーションバーの正しいHTML構造例作成
  - ✅ 実装チェックリストに追加
- ✅ Flask-WTF削除版requirements.txt確定
- ✅ セキュリティヘッダー設定実装例作成
- ✅ CSRF実装設計書作成（Step 3.2向け）
- ✅ python-dotenv使用ガイドライン作成
- ✅ **UI共通コンポーネント詳細仕様作成（H-3対応）**
  - ✅ プログレスインジケーター仕様（Bootstrap 5.3準拠）
  - ✅ トースト通知仕様（4種類：成功/エラー/警告/情報）
  - ✅ モーダルダイアログ仕様（3種類：削除確認/一括追加/エラー詳細）
  - ✅ jQuery + Vanilla JS 両方のコード例
  - ✅ アクセシビリティ考慮事項（ARIA属性完備）
  - ✅ base.html設計に3つのコンポーネント領域を統合
  - ✅ 実装チェックリストにUI共通コンポーネント検証項目を追加
- ✅ ロールバック手順書作成（H-4対応）

**次のアクション**: Step 3.1実装開始（templates/base.html作成 + セキュリティヘッダー設定）
