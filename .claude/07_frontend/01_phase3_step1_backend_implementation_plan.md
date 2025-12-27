# Phase 3 Step 3.1: バックエンド実装計画（修正版）

**最終更新日**: 2025-12-27
**ステータス**: 修正完了
**次のステップ**: Step 3.1実装（base.html作成のみ、Flask-WTF導入なし）

## 修正内容サマリー

### 修正対象問題（5件）

| ID | 重要度 | 問題内容 | 修正状況 |
|----|--------|---------|---------|
| C-2 | Critical | Flask-WTF導入タイミング | ✅ Step 3.2以降に延期 |
| C-3 | Critical | CSRF実装方法未決定 | ✅ Meta+Fetchヘッダー方式を採用 |
| H-1 | High | python-dotenv二重管理 | ✅ Docker環境では不要と明確化 |
| H-2 | High | セキュリティヘッダー非推奨 | ✅ CSP等現代的ヘッダーに更新 |
| H-4 | High | ロールバック戦略未策定 | ✅ Git運用手順を策定 |

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

## Step 3.1実装スコープ（修正版）

### 実装対象

**1. ベーステンプレート（templates/base.html）**:
- [ ] HTML5基本構造
- [ ] Bootstrap 5.3 CDN読込
- [ ] jQuery 3.7+ CDN読込
- [ ] ナビゲーションバー（メイン/マッピング管理リンク）
- [ ] フッター
- [ ] コンテンツブロック定義（`{% block content %}`）
- [ ] スクリプトブロック定義（`{% block scripts %}`）

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
- [ ] セキュリティヘッダー確認（`curl -I`）
- [ ] ChromeデベロッパーツールでCSP警告確認

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
| C-2 | Flask-WTF導入タイミング | Step 3.2以降に延期 | ✅ 完了 |
| C-3 | CSRF実装方法 | Meta+Fetchヘッダー方式採用、設計書作成 | ✅ 完了 |
| H-1 | python-dotenv二重管理 | Docker環境では不要と明確化 | ✅ 完了 |
| H-2 | セキュリティヘッダー非推奨 | CSP等現代的ヘッダーに更新 | ✅ 完了 |
| H-4 | ロールバック戦略 | Git運用規約・手順書作成 | ✅ 完了 |

### Step 3.1実装準備完了

- ✅ 修正版実装計画書作成
- ✅ Flask-WTF削除版requirements.txt確定
- ✅ セキュリティヘッダー設定実装例作成
- ✅ CSRF実装設計書作成（Step 3.2向け）
- ✅ python-dotenv使用ガイドライン作成
- ✅ ロールバック手順書作成

**次のアクション**: Step 3.1実装開始（backend-code-generatorエージェント使用）
