# Phase 3 Step 3.2: メイン画面実装計画（templates/index.html）

**作成日**: 2025-12-29
**対象**: templates/index.html、static/js/index.js（新規）、static/css/index.css（オプション）

## 1. 実装概要

### 1.1 目的
イオンカード明細CSVファイルの取り込みから、Google Sheetsへの反映、処理結果表示までを一画面で完結させるメイン画面を実装します。

### 1.2 実装方針
- **プログレッシブディスクロージャー**: ユーザーの操作に応じて段階的に情報を開示
- **レスポンシブデザイン**: Bootstrap 5.3のグリッドシステムを活用
- **アクセシビリティ**: ARIA属性、role属性、キーボードナビゲーション対応
- **エラーハンドリング**: 各操作段階での適切なエラーフィードバック

### 1.3 画面フロー
```
1. CSVファイル選択 → ファイル名表示
2. プレビューボタンクリック → サーバーへプレビューリクエスト → プレビュー表示
3. スプレッドシート設定（ID、対象年入力）
4. 取込実行ボタンクリック → サーバーへ処理リクエスト → 結果表示
5. 結果確認（サマリー、未登録店舗リスト、ログダウンロード）
```

---

## 2. HTML構造設計

### 2.1 全体構成
```html
{% extends 'base.html' %}

{% block title %}CSV取込 - {{ super() }}{% endblock %}

{% block content %}
  <div class="container py-4">
    <h1>CSV取込メイン画面</h1>

    <!-- Step 1: CSVファイル選択エリア -->
    <section id="fileSelectionArea">...</section>

    <!-- Step 2: プレビューエリア（初期非表示） -->
    <section id="previewArea" class="d-none">...</section>

    <!-- Step 3: スプレッドシート設定エリア（初期非表示） -->
    <section id="settingsArea" class="d-none">...</section>

    <!-- Step 4: 実行ボタンエリア（初期非表示） -->
    <section id="executeArea" class="d-none">...</section>

    <!-- Step 5: 結果表示エリア（初期非表示） -->
    <section id="resultArea" class="d-none">...</section>
  </div>
{% endblock %}

{% block scripts %}
  <script src="{{ url_for('static', filename='js/index.js') }}"></script>
{% endblock %}
```

### 2.2 各セクション詳細

#### 2.2.1 CSVファイル選択エリア
```html
<section id="fileSelectionArea" class="card mb-4" aria-labelledby="fileSelectionTitle">
  <div class="card-header bg-primary text-white">
    <h2 class="h5 mb-0" id="fileSelectionTitle">
      <i class="bi bi-file-earmark-arrow-up"></i> Step 1: CSVファイル選択
    </h2>
  </div>
  <div class="card-body">
    <!-- ファイル選択フォーム -->
    <form id="uploadForm" enctype="multipart/form-data">
      <div class="mb-3">
        <label for="csvFile" class="form-label">
          イオンカード利用明細CSVファイル（Shift_JIS形式）
        </label>
        <input
          type="file"
          class="form-control"
          id="csvFile"
          name="csv_file"
          accept=".csv"
          required
          aria-describedby="fileHelp"
        >
        <div id="fileHelp" class="form-text">
          ファイルサイズ上限: 10MB | 対応形式: CSV（Shift_JIS）
        </div>
        <!-- バリデーションエラー表示 -->
        <div class="invalid-feedback">
          CSVファイルを選択してください。
        </div>
      </div>

      <!-- 選択ファイル名表示 -->
      <div id="selectedFileInfo" class="alert alert-info d-none" role="status">
        <i class="bi bi-file-earmark-text"></i>
        選択ファイル: <strong id="selectedFileName"></strong>
        （<span id="selectedFileSize"></span>）
      </div>

      <!-- プレビューボタン -->
      <button
        type="button"
        id="previewBtn"
        class="btn btn-outline-primary"
        disabled
      >
        <i class="bi bi-eye"></i> プレビュー表示
      </button>
    </form>
  </div>
</section>
```

**ポイント**:
- `accept=".csv"`: ファイル選択ダイアログでCSVのみ表示
- `required`: HTML5バリデーション
- `aria-describedby`: スクリーンリーダー対応
- `disabled`: ファイル未選択時は無効化

#### 2.2.2 プレビューエリア
```html
<section id="previewArea" class="card mb-4 d-none" aria-labelledby="previewTitle">
  <div class="card-header bg-success text-white">
    <h2 class="h5 mb-0" id="previewTitle">
      <i class="bi bi-eye"></i> Step 2: データプレビュー
    </h2>
  </div>
  <div class="card-body">
    <!-- プレビュー統計情報 -->
    <div class="row mb-3">
      <div class="col-md-4">
        <div class="text-center p-3 bg-light rounded">
          <div class="h3 text-primary mb-0" id="previewTotalCount">0</div>
          <div class="text-muted small">総件数</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="text-center p-3 bg-light rounded">
          <div class="h3 text-success mb-0" id="previewTotalAmount">0円</div>
          <div class="text-muted small">総金額</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="text-center p-3 bg-light rounded">
          <div class="h6 mb-0">
            <span id="previewDateRange" class="text-secondary">-</span>
          </div>
          <div class="text-muted small">期間</div>
        </div>
      </div>
    </div>

    <!-- プレビューテーブル -->
    <div class="table-responsive">
      <table class="table table-striped table-hover" role="table">
        <caption class="visually-hidden">明細データプレビュー（先頭5件）</caption>
        <thead class="table-light">
          <tr>
            <th scope="col">利用日</th>
            <th scope="col">店舗名</th>
            <th scope="col" class="text-end">金額</th>
          </tr>
        </thead>
        <tbody id="previewTableBody">
          <!-- JavaScriptで動的生成 -->
        </tbody>
      </table>
    </div>

    <p class="text-muted small mb-0">
      <i class="bi bi-info-circle"></i> 先頭5件のみ表示しています
    </p>
  </div>
</section>
```

**ポイント**:
- `d-none`: 初期非表示（JavaScriptで表示制御）
- `table-responsive`: モバイル対応のテーブル
- `role="table"`, `caption`: アクセシビリティ対応
- 統計情報カード: Bootstrap 5のgrid、card

#### 2.2.3 スプレッドシート設定エリア
```html
<section id="settingsArea" class="card mb-4 d-none" aria-labelledby="settingsTitle">
  <div class="card-header bg-info text-white">
    <h2 class="h5 mb-0" id="settingsTitle">
      <i class="bi bi-gear"></i> Step 3: スプレッドシート設定
    </h2>
  </div>
  <div class="card-body">
    <form id="settingsForm" novalidate>
      <!-- スプレッドシートID入力 -->
      <div class="mb-3">
        <label for="spreadsheetId" class="form-label">
          スプレッドシートID <span class="text-danger">*</span>
        </label>
        <input
          type="text"
          class="form-control"
          id="spreadsheetId"
          name="spreadsheet_id"
          placeholder="例: 10RJcB-_pOqsxA-6mGZ..."
          required
          pattern="[A-Za-z0-9_-]{30,}"
          aria-describedby="spreadsheetIdHelp"
        >
        <div id="spreadsheetIdHelp" class="form-text">
          GoogleスプレッドシートのURL内のIDをコピーしてください
        </div>
        <div class="invalid-feedback">
          有効なスプレッドシートIDを入力してください（30文字以上の英数字、ハイフン、アンダースコア）
        </div>
      </div>

      <!-- 対象年選択 -->
      <div class="mb-3">
        <label for="targetYear" class="form-label">
          対象年 <span class="text-danger">*</span>
        </label>
        <select
          class="form-select"
          id="targetYear"
          name="target_year"
          required
        >
          <option value="">年を選択してください</option>
          <option value="2023">2023年</option>
          <option value="2024">2024年</option>
          <option value="2025" selected>2025年</option>
          <option value="2026">2026年</option>
        </select>
        <div class="invalid-feedback">
          対象年を選択してください
        </div>
      </div>

      <!-- サービスアカウント情報表示 -->
      <div class="alert alert-light" role="status">
        <h3 class="h6">
          <i class="bi bi-info-circle-fill text-info"></i> サービスアカウント情報
        </h3>
        <p class="mb-1 small">
          <strong>メールアドレス:</strong>
          <code>creditapi@creditapi-470614.iam.gserviceaccount.com</code>
        </p>
        <p class="mb-0 small text-muted">
          スプレッドシートに上記アカウントの編集権限を付与してください
        </p>
      </div>
    </form>
  </div>
</section>
```

**ポイント**:
- `pattern`: スプレッドシートIDの形式バリデーション
- `novalidate`: カスタムバリデーション（JavaScriptで制御）
- `<span class="text-danger">*</span>`: 必須項目マーク
- サービスアカウント情報: ユーザーガイダンス

#### 2.2.4 実行ボタンエリア
```html
<section id="executeArea" class="card mb-4 d-none" aria-labelledby="executeTitle">
  <div class="card-header bg-warning">
    <h2 class="h5 mb-0" id="executeTitle">
      <i class="bi bi-play-fill"></i> Step 4: 取込実行
    </h2>
  </div>
  <div class="card-body text-center">
    <p>設定内容を確認の上、取込を実行してください。</p>

    <!-- 実行ボタン -->
    <button
      type="button"
      id="executeBtn"
      class="btn btn-warning btn-lg"
    >
      <i class="bi bi-upload"></i> 取込実行
    </button>

    <!-- プログレス表示（base.htmlのプログレスインジケーターを使用） -->
  </div>
</section>
```

**ポイント**:
- `btn-lg`: 大きめのボタンで視認性向上
- プログレス表示は`base.html`の`#progressIndicator`を使用

#### 2.2.5 結果表示エリア
```html
<section id="resultArea" class="card mb-4 d-none" aria-labelledby="resultTitle">
  <div class="card-header bg-success text-white">
    <h2 class="h5 mb-0" id="resultTitle">
      <i class="bi bi-check-circle"></i> Step 5: 処理結果
    </h2>
  </div>
  <div class="card-body">
    <!-- 処理サマリー -->
    <div class="alert alert-success" role="status">
      <h3 class="h5">
        <i class="bi bi-check-circle-fill"></i> 処理完了
      </h3>
      <p class="mb-0">
        合計 <strong id="resultTotalCount">0</strong>件 /
        <strong id="resultTotalAmount">0円</strong> を反映しました
        （処理時間: <span id="resultProcessingTime">0</span>秒）
      </p>
    </div>

    <!-- 月別・カテゴリ別サマリーテーブル -->
    <h3 class="h6 mt-4 mb-3">月別・カテゴリ別サマリー</h3>
    <div class="table-responsive">
      <table class="table table-bordered table-sm" role="table">
        <caption class="visually-hidden">月別・カテゴリ別処理サマリー</caption>
        <thead class="table-light">
          <tr>
            <th scope="col">月</th>
            <th scope="col">カテゴリ</th>
            <th scope="col">列</th>
            <th scope="col" class="text-end">件数</th>
            <th scope="col" class="text-end">金額</th>
          </tr>
        </thead>
        <tbody id="resultSummaryTableBody">
          <!-- JavaScriptで動的生成 -->
        </tbody>
      </table>
    </div>

    <!-- 未登録店舗リスト -->
    <div id="unregisteredStoresSection" class="mt-4 d-none">
      <h3 class="h6 mb-3">
        <i class="bi bi-exclamation-triangle-fill text-warning"></i> 未登録店舗
      </h3>
      <div class="alert alert-warning" role="status">
        <p class="mb-2">
          以下の店舗はマッピングに登録されていません。
          確認画面でカテゴリを設定してください。
        </p>
        <ul id="unregisteredStoresList" class="mb-2">
          <!-- JavaScriptで動的生成 -->
        </ul>
        <a href="{{ url_for('mapping') }}" class="btn btn-sm btn-warning">
          <i class="bi bi-list-ul"></i> マッピング管理画面で登録
        </a>
      </div>
    </div>

    <!-- ログダウンロードボタン -->
    <div class="text-center mt-4">
      <a
        href="{{ url_for('download_log') }}"
        class="btn btn-outline-secondary"
        download
      >
        <i class="bi bi-download"></i> 詳細ログをダウンロード
      </a>
    </div>
  </div>
</section>
```

**ポイント**:
- 動的コンテンツ: JavaScriptでサーバーレスポンスを元に生成
- 未登録店舗: 条件付き表示（`d-none`で初期非表示）
- マッピング管理画面へのリンク: スムーズな導線

---

## 3. JavaScript機能設計（static/js/index.js）

### 3.1 全体構成
```javascript
(function() {
  'use strict';

  // =========================================
  // 定数定義
  // =========================================
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const ALLOWED_EXTENSIONS = ['csv'];

  // =========================================
  // DOMContentLoaded後の初期化
  // =========================================
  document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
  });

  // =========================================
  // イベントリスナー初期化
  // =========================================
  function initializeEventListeners() {
    // ファイル選択イベント
    document.getElementById('csvFile').addEventListener('change', handleFileSelect);

    // プレビューボタンクリック
    document.getElementById('previewBtn').addEventListener('click', handlePreview);

    // 取込実行ボタンクリック
    document.getElementById('executeBtn').addEventListener('click', handleExecute);
  }

  // =========================================
  // ファイル選択ハンドラー
  // =========================================
  function handleFileSelect(event) { ... }

  // =========================================
  // プレビューハンドラー
  // =========================================
  function handlePreview() { ... }

  // =========================================
  // 取込実行ハンドラー
  // =========================================
  function handleExecute() { ... }

  // =========================================
  // ヘルパー関数
  // =========================================
  function validateFile(file) { ... }
  function formatFileSize(bytes) { ... }
  function formatCurrency(amount) { ... }
  function updatePreviewDisplay(data) { ... }
  function updateResultDisplay(data) { ... }
  function showSection(sectionId) { ... }
  function hideSection(sectionId) { ... }

})();
```

### 3.2 各関数の詳細仕様

#### 3.2.1 handleFileSelect - ファイル選択処理
```javascript
function handleFileSelect(event) {
  const file = event.target.files[0];

  if (!file) {
    // ファイル未選択時
    document.getElementById('selectedFileInfo').classList.add('d-none');
    document.getElementById('previewBtn').disabled = true;
    return;
  }

  // バリデーション
  const validation = validateFile(file);
  if (!validation.valid) {
    window.showToast('#errorToast', validation.message);
    event.target.value = ''; // ファイル選択クリア
    return;
  }

  // ファイル情報表示
  document.getElementById('selectedFileName').textContent = file.name;
  document.getElementById('selectedFileSize').textContent = formatFileSize(file.size);
  document.getElementById('selectedFileInfo').classList.remove('d-none');

  // プレビューボタン有効化
  document.getElementById('previewBtn').disabled = false;

  // プレビュー以降のセクションを非表示
  hideSection('previewArea');
  hideSection('settingsArea');
  hideSection('executeArea');
  hideSection('resultArea');
}
```

**処理フロー**:
1. ファイル取得
2. バリデーション（拡張子、サイズ）
3. ファイル情報表示
4. プレビューボタン有効化
5. 以降のセクション非表示

#### 3.2.2 handlePreview - プレビュー処理
```javascript
async function handlePreview() {
  const fileInput = document.getElementById('csvFile');
  const file = fileInput.files[0];

  if (!file) {
    window.showToast('#errorToast', 'ファイルを選択してください');
    return;
  }

  // プログレス表示
  window.showProgress();

  try {
    // Step 1: ファイルアップロード（POST /upload）
    const uploadFormData = new FormData();
    uploadFormData.append('csv_file', file);

    const uploadResponse = await fetch('/upload', {
      method: 'POST',
      body: uploadFormData
    });

    if (!uploadResponse.ok) {
      const errorData = await uploadResponse.json();
      throw new Error(errorData.message || 'アップロードに失敗しました');
    }

    const uploadResult = await uploadResponse.json();

    // Step 2: プレビュー取得（POST /preview）
    const previewResponse = await fetch('/preview', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!previewResponse.ok) {
      const errorData = await previewResponse.json();
      throw new Error(errorData.message || 'プレビュー取得に失敗しました');
    }

    const previewResult = await previewResponse.json();

    // プレビュー表示更新
    updatePreviewDisplay(previewResult.data);

    // 次のセクション表示
    showSection('previewArea');
    showSection('settingsArea');
    showSection('executeArea');

    // スムーズスクロール
    document.getElementById('previewArea').scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });

    window.showToast('#successToast', 'プレビューを表示しました');

  } catch (error) {
    console.error('Preview error:', error);
    window.showToast('#errorToast', error.message);
  } finally {
    window.hideProgress();
  }
}
```

**処理フロー**:
1. プログレス表示開始
2. `/upload` APIでファイルアップロード
3. `/preview` APIでプレビューデータ取得
4. プレビュー表示更新
5. 設定・実行セクション表示
6. プログレス非表示
7. トースト通知

#### 3.2.3 handleExecute - 取込実行処理
```javascript
async function handleExecute() {
  // フォームバリデーション
  const settingsForm = document.getElementById('settingsForm');
  if (!window.validateForm(settingsForm)) {
    window.showToast('#errorToast', '設定内容を確認してください');
    return;
  }

  const spreadsheetId = document.getElementById('spreadsheetId').value.trim();
  const targetYear = parseInt(document.getElementById('targetYear').value);

  // 確認ダイアログ
  if (!confirm(`${targetYear}年のスプレッドシートにデータを反映します。よろしいですか？`)) {
    return;
  }

  // プログレス表示
  window.showProgress();

  try {
    // POST /process API呼び出し
    const response = await fetch('/process', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        spreadsheet_id: spreadsheetId,
        target_year: targetYear
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || '処理に失敗しました');
    }

    const result = await response.json();

    // 結果表示更新
    updateResultDisplay(result.data);

    // 結果セクション表示
    showSection('resultArea');

    // スムーズスクロール
    document.getElementById('resultArea').scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });

    window.showToast('#successToast', '取込処理が完了しました');

  } catch (error) {
    console.error('Execute error:', error);
    window.showToast('#errorToast', error.message);
  } finally {
    window.hideProgress();
  }
}
```

**処理フロー**:
1. フォームバリデーション
2. 確認ダイアログ
3. プログレス表示開始
4. `/process` APIで処理実行
5. 結果表示更新
6. 結果セクション表示
7. プログレス非表示
8. トースト通知

#### 3.2.4 ヘルパー関数

**validateFile - ファイルバリデーション**
```javascript
function validateFile(file) {
  // 拡張子チェック
  const extension = file.name.split('.').pop().toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return {
      valid: false,
      message: 'CSVファイルのみアップロード可能です'
    };
  }

  // サイズチェック
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      message: `ファイルサイズが10MBを超えています（${formatFileSize(file.size)}）`
    };
  }

  return { valid: true };
}
```

**formatFileSize - ファイルサイズフォーマット**
```javascript
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
```

**formatCurrency - 通貨フォーマット**
```javascript
function formatCurrency(amount) {
  return new Intl.NumberFormat('ja-JP', {
    style: 'currency',
    currency: 'JPY'
  }).format(amount);
}
```

**updatePreviewDisplay - プレビュー表示更新**
```javascript
function updatePreviewDisplay(data) {
  // 統計情報更新
  document.getElementById('previewTotalCount').textContent = data.total_count;
  document.getElementById('previewTotalAmount').textContent = formatCurrency(data.total_amount);
  document.getElementById('previewDateRange').textContent =
    `${data.date_range.start} ～ ${data.date_range.end}`;

  // テーブル更新
  const tbody = document.getElementById('previewTableBody');
  tbody.innerHTML = '';

  data.preview.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(row.date)}</td>
      <td>${escapeHtml(row.store)}</td>
      <td class="text-end">${formatCurrency(row.amount)}</td>
    `;
    tbody.appendChild(tr);
  });
}
```

**updateResultDisplay - 結果表示更新**
```javascript
function updateResultDisplay(data) {
  // サマリー情報更新
  document.getElementById('resultTotalCount').textContent = data.summary.total_count;
  document.getElementById('resultTotalAmount').textContent = formatCurrency(data.summary.total_amount);
  document.getElementById('resultProcessingTime').textContent =
    data.processing_time.toFixed(2);

  // 月別・カテゴリ別サマリーテーブル更新
  const summaryTbody = document.getElementById('resultSummaryTableBody');
  summaryTbody.innerHTML = '';

  Object.entries(data.summary.by_month).forEach(([month, monthData]) => {
    Object.entries(monthData.by_category).forEach(([category, categoryData]) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${month}月</td>
        <td>${escapeHtml(category)}</td>
        <td>${escapeHtml(categoryData.column)}</td>
        <td class="text-end">${categoryData.count}件</td>
        <td class="text-end">${formatCurrency(categoryData.amount)}</td>
      `;
      summaryTbody.appendChild(tr);
    });
  });

  // 未登録店舗リスト更新
  if (data.unregistered_stores && data.unregistered_stores.length > 0) {
    const unregisteredList = document.getElementById('unregisteredStoresList');
    unregisteredList.innerHTML = '';

    data.unregistered_stores.forEach(store => {
      const li = document.createElement('li');
      li.textContent = `${escapeHtml(store.store_name)} (${formatCurrency(store.total_amount)}, ${store.count}件)`;
      unregisteredList.appendChild(li);
    });

    document.getElementById('unregisteredStoresSection').classList.remove('d-none');
  } else {
    document.getElementById('unregisteredStoresSection').classList.add('d-none');
  }
}
```

**showSection / hideSection - セクション表示制御**
```javascript
function showSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (section) {
    section.classList.remove('d-none');
  }
}

function hideSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (section) {
    section.classList.add('d-none');
  }
}
```

**escapeHtml - XSS対策**
```javascript
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.toString().replace(/[&<>"']/g, m => map[m]);
}
```

---

## 4. API連携仕様

### 4.1 POST /upload
**リクエスト**:
```
Content-Type: multipart/form-data
Body: { csv_file: File }
```

**レスポンス（成功）**:
```json
{
  "status": "success",
  "data": {
    "filename": "meisai.csv",
    "file_path": "/app/uploads/20251229_123456_meisai.csv",
    "file_size": 12345
  },
  "message": "ファイルのアップロードに成功しました"
}
```

**レスポンス（エラー）**:
```json
{
  "status": "error",
  "message": "CSVファイルのみアップロード可能です"
}
```

### 4.2 POST /preview
**リクエスト**:
```
Content-Type: application/json
Body: なし（セッションからファイルパス取得）
```

**レスポンス（成功）**:
```json
{
  "status": "success",
  "data": {
    "preview": [
      {
        "date": "2025/08/03",
        "store": "ユシンヤ",
        "amount": 1890
      },
      ...
    ],
    "total_count": 17,
    "total_amount": 27575,
    "date_range": {
      "start": "2025/08/01",
      "end": "2025/08/31"
    }
  },
  "message": "プレビューデータを取得しました"
}
```

### 4.3 POST /process
**リクエスト**:
```json
{
  "spreadsheet_id": "10RJcB-_pOqsxA-6mGZ...",
  "target_year": 2025
}
```

**レスポンス（成功）**:
```json
{
  "status": "success",
  "data": {
    "summary": {
      "total_amount": 27575,
      "total_count": 17,
      "by_category": {
        "食材費": { "amount": 11560, "count": 8, "column": "C" },
        "外食費": { "amount": 7045, "count": 5, "column": "D" }
      },
      "by_month": {
        "8": {
          "amount": 27575,
          "count": 17,
          "by_category": { ... }
        }
      }
    },
    "unregistered_stores": [
      {
        "store_name": "デイーエムエム",
        "total_amount": 300,
        "count": 1
      }
    ],
    "updated_cells": 4,
    "processing_time": 2.35
  },
  "message": "処理が完了しました"
}
```

### 4.4 GET /download/log
**レスポンス**: ログファイル（text/plain）

---

## 5. セキュリティ対策

### 5.1 CSRF対策（Meta+Fetchヘッダー方式）
**実装方法**:
- `base.html`の`<head>`内にCSRFトークンをMetaタグで埋め込み
- すべてのPOSTリクエストにCSRFトークンヘッダーを付与

**base.html修正（Step 3.2で実施）**:
```html
<head>
  <!-- 既存のhead要素 -->
  <meta name="csrf-token" content="{{ csrf_token() }}">
</head>
```

**index.js修正**:
```javascript
// Fetch APIのデフォルトヘッダーにCSRFトークン追加
function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

// すべてのPOSTリクエストに適用
const response = await fetch('/preview', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': getCsrfToken()
  }
});
```

**注意**: 現時点では、FlaskアプリにCSRFトークン生成機能が未実装のため、Step 3.2実装時に以下を追加する必要があります:
- `flask-wtf`のインストール（requirements.txtに追加）
- `app.py`にCSRFProtection設定
- Jinja2テンプレートで`csrf_token()`関数使用

### 5.2 XSS対策
- **出力エスケープ**: すべてのユーザー入力・APIレスポンスデータを`escapeHtml()`でエスケープ
- **Jinja2自動エスケープ**: デフォルトで有効（`{{ variable }}`は自動エスケープ）

### 5.3 ファイルアップロードセキュリティ
- **拡張子チェック**: クライアント側（`accept=".csv"`）+ サーバー側（`allowed_file()`）
- **ファイルサイズ制限**: クライアント側（JavaScript）+ サーバー側（Flask MAX_CONTENT_LENGTH）
- **ファイル名サニタイズ**: サーバー側で`secure_filename()`使用

### 5.4 入力バリデーション
- **HTML5バリデーション**: `required`, `pattern`属性
- **JavaScriptバリデーション**: `validateForm()`関数
- **サーバー側バリデーション**: app.pyのエンドポイントで実施

---

## 6. エラーハンドリング

### 6.1 エラー種別と対応

| エラー種別 | 発生タイミング | 表示方法 | ユーザーアクション |
|-----------|--------------|---------|------------------|
| ファイル未選択 | プレビュークリック時 | エラートースト | ファイル選択 |
| 不正な拡張子 | ファイル選択時 | エラートースト | 正しいファイル選択 |
| ファイルサイズ超過 | ファイル選択時 | エラートースト | ファイルサイズ削減 |
| アップロードエラー | /upload API呼び出し時 | エラートースト | 再試行 |
| CSV解析エラー | /preview API呼び出し時 | エラートースト | 正しいCSVファイル選択 |
| 設定未入力 | 取込実行時 | フォームバリデーション + エラートースト | 設定入力 |
| スプレッドシート接続エラー | /process API呼び出し時 | エラートースト + エラー詳細モーダル | 設定確認 |
| ネットワークエラー | API呼び出し時 | エラートースト | 再試行 |

### 6.2 エラー表示パターン

**パターン1: トースト通知（軽微なエラー）**
```javascript
window.showToast('#errorToast', 'ファイルを選択してください');
```

**パターン2: フォームバリデーション（入力エラー）**
```javascript
if (!window.validateForm(settingsForm)) {
  // Bootstrap の .was-validated クラスで視覚的にエラー表示
  settingsForm.classList.add('was-validated');
}
```

**パターン3: エラー詳細モーダル（重大なエラー）**
```javascript
function showErrorDetail(errorMessage, errorDetails) {
  document.getElementById('errorDetailContent').textContent =
    `${errorMessage}\n\n詳細:\n${errorDetails}`;
  const modal = new bootstrap.Modal(document.getElementById('errorDetailModal'));
  modal.show();
}
```

### 6.3 リトライ機構
- ネットワークエラー時は、ユーザーに再試行を促す
- APIリクエストは冪等性を確保（同じリクエストを複数回実行しても結果が同じ）

---

## 7. UI/UX設計

### 7.1 プログレッシブディスクロージャー
**原則**: ユーザーが必要とする情報を、必要なタイミングで開示

**実装**:
- Step 1（ファイル選択）は常に表示
- Step 2（プレビュー）はファイル選択後に表示
- Step 3（設定）はプレビュー取得後に表示
- Step 4（実行）は設定入力後に表示
- Step 5（結果）は処理完了後に表示

### 7.2 レスポンシブデザイン
**Bootstrapグリッドシステム**:
- `container`: 中央揃えコンテナ
- `row`, `col-md-*`: グリッドレイアウト
- `d-none`, `d-md-block`: ブレークポイント別表示制御

**モバイルファースト**:
- タッチターゲットサイズ: 最低44x44px
- フォント読みやすさ: 最低16px
- テーブルレスポンシブ: `table-responsive`クラス

### 7.3 アクセシビリティ（WCAG 2.1 AAレベル）

**実装内容**:
- **スキップリンク**: `<a href="#main-content" class="visually-hidden-focusable">`
- **ARIA属性**:
  - `role="status"`: 動的に変化する情報
  - `aria-labelledby`: セクション見出し関連付け
  - `aria-describedby`: 入力項目の説明関連付け
  - `aria-live="polite"`: プログレスインジケーター
- **キーボードナビゲーション**: すべてのインタラクティブ要素がキーボード操作可能
- **フォーカス管理**: モーダル表示時、最初の入力要素にフォーカス
- **カラーコントラスト**: Bootstrap 5.3のデフォルトカラーはWCAG AA準拠

### 7.4 ローディング表示
**プログレスインジケーター**:
- `base.html`の`#progressIndicator`を使用
- API呼び出し前に`window.showProgress()`
- 完了後に`window.hideProgress()`

**ボタン無効化**:
- 処理中は実行ボタンを無効化（二重送信防止）

### 7.5 スムーズスクロール
**実装**:
```javascript
element.scrollIntoView({ behavior: 'smooth', block: 'start' });
```

**使用タイミング**:
- プレビュー表示後、プレビューセクションへスクロール
- 結果表示後、結果セクションへスクロール

---

## 8. テスト項目リスト

### 8.1 UI操作テスト

| テストケース | 操作内容 | 期待結果 |
|------------|---------|---------|
| TC-001 | ページロード | Step 1のみ表示、他セクション非表示 |
| TC-002 | CSVファイル選択（正常） | ファイル情報表示、プレビューボタン有効化 |
| TC-003 | 非CSVファイル選択 | エラートースト表示、ファイル選択クリア |
| TC-004 | 10MB超ファイル選択 | エラートースト表示、ファイル選択クリア |
| TC-005 | プレビューボタンクリック | プログレス表示 → プレビュー表示 → 設定・実行セクション表示 |
| TC-006 | スプレッドシートID未入力で実行 | フォームバリデーションエラー表示 |
| TC-007 | 対象年未選択で実行 | フォームバリデーションエラー表示 |
| TC-008 | 取込実行ボタンクリック | 確認ダイアログ → プログレス表示 → 結果表示 |
| TC-009 | 未登録店舗あり | 未登録店舗セクション表示 |
| TC-010 | 未登録店舗なし | 未登録店舗セクション非表示 |

### 8.2 API連携テスト

| テストケース | API | 条件 | 期待結果 |
|------------|-----|------|---------|
| TC-011 | POST /upload | 正常なCSVファイル | 200 OK、ファイル情報返却 |
| TC-012 | POST /upload | ファイル未送信 | 400 Bad Request、エラーメッセージ |
| TC-013 | POST /preview | 正常なCSVデータ | 200 OK、プレビューデータ返却 |
| TC-014 | POST /preview | CSV未アップロード | 400 Bad Request、エラーメッセージ |
| TC-015 | POST /process | 正常な設定 | 200 OK、処理結果返却 |
| TC-016 | POST /process | スプレッドシートID不正 | 400 Bad Request、エラーメッセージ |
| TC-017 | POST /process | 対象年不正 | 400 Bad Request、エラーメッセージ |
| TC-018 | GET /download/log | - | 200 OK、ログファイルダウンロード |

### 8.3 レスポンシブデザインテスト

| テストケース | デバイス | 期待結果 |
|------------|---------|---------|
| TC-019 | デスクトップ（1920x1080） | 3カラムレイアウト、すべて正常表示 |
| TC-020 | タブレット（768x1024） | 2カラムレイアウト、テーブル横スクロール |
| TC-021 | モバイル（375x667） | 1カラムレイアウト、タッチターゲット44px以上 |

### 8.4 アクセシビリティテスト

| テストケース | 操作 | 期待結果 |
|------------|-----|---------|
| TC-022 | Tabキーナビゲーション | すべてのインタラクティブ要素にフォーカス可能 |
| TC-023 | スクリーンリーダー（NVDA） | すべてのセクション見出し読み上げ |
| TC-024 | キーボードのみでファイル選択 | Enterキーでファイル選択ダイアログ表示 |
| TC-025 | カラーコントラスト測定 | すべてのテキストがWCAG AA準拠（4.5:1以上） |

### 8.5 エラーハンドリングテスト

| テストケース | エラー条件 | 期待結果 |
|------------|----------|---------|
| TC-026 | ネットワークエラー（/upload） | エラートースト表示、リトライ促進 |
| TC-027 | ネットワークエラー（/preview） | エラートースト表示、リトライ促進 |
| TC-028 | ネットワークエラー（/process） | エラートースト表示、リトライ促進 |
| TC-029 | CSV解析エラー | エラートースト表示、詳細エラーメッセージ |
| TC-030 | Google Sheets接続エラー | エラートースト + エラー詳細モーダル |

### 8.6 セキュリティテスト

| テストケース | 攻撃手法 | 期待結果 |
|------------|---------|---------|
| TC-031 | XSS（店舗名に`<script>`タグ） | エスケープされて無害化 |
| TC-032 | ファイルサイズ超過攻撃（100MB） | クライアント側でブロック |
| TC-033 | 不正な拡張子（.exe） | クライアント側でブロック |
| TC-034 | CSRF攻撃（外部サイトから/process呼び出し） | CSRFトークン検証でブロック |

---

## 9. 実装スケジュール

### 9.1 Phase 1: HTML構造実装（2時間）
- [ ] templates/index.html 作成
- [ ] 5つのセクション実装（Step 1～5）
- [ ] Bootstrapクラス適用
- [ ] ARIA属性追加

### 9.2 Phase 2: JavaScript基礎実装（3時間）
- [ ] static/js/index.js 作成
- [ ] イベントリスナー設定
- [ ] ファイル選択処理
- [ ] バリデーション処理
- [ ] ヘルパー関数実装

### 9.3 Phase 3: API連携実装（3時間）
- [ ] /upload API連携
- [ ] /preview API連携
- [ ] /process API連携
- [ ] エラーハンドリング
- [ ] プログレス表示

### 9.4 Phase 4: 表示更新実装（2時間）
- [ ] プレビュー表示更新
- [ ] 結果表示更新
- [ ] 未登録店舗リスト表示
- [ ] セクション表示制御

### 9.5 Phase 5: セキュリティ対策（2時間）
- [ ] CSRF対策（Meta+Fetchヘッダー方式）
- [ ] XSS対策（エスケープ処理）
- [ ] 入力バリデーション強化

### 9.6 Phase 6: テスト・調整（2時間）
- [ ] ブラウザテスト（Chrome, Firefox, Edge）
- [ ] レスポンシブテスト
- [ ] アクセシビリティテスト
- [ ] エラーハンドリングテスト

**総所要時間**: 約14時間

---

## 10. 関連ファイル

### 10.1 実装ファイル
- `C:\work\Lesson\個人開発\Crdit_detail\templates\index.html`（新規作成）
- `C:\work\Lesson\個人開発\Crdit_detail\static\js\index.js`（新規作成）
- `C:\work\Lesson\個人開発\Crdit_detail\static\css\index.css`（オプション、必要に応じて作成）

### 10.2 既存ファイル（Step 3.1で作成済み）
- `C:\work\Lesson\個人開発\Crdit_detail\templates\base.html`（継承元）
- `C:\work\Lesson\個人開発\Crdit_detail\static\css\style.css`（共通CSS）
- `C:\work\Lesson\個人開発\Crdit_detail\static\js\main.js`（共通JavaScript）

### 10.3 バックエンド（Phase 2で作成済み）
- `C:\work\Lesson\個人開発\Crdit_detail\app.py`（APIエンドポイント）
- `C:\work\Lesson\個人開発\Crdit_detail\modules\csv_processor.py`（CSV処理）
- `C:\work\Lesson\個人開発\Crdit_detail\modules\category_logic.py`（カテゴリ判定）
- `C:\work\Lesson\個人開発\Crdit_detail\modules\sheets_api.py`（Google Sheets連携）

### 10.4 参照ドキュメント
- `.claude/00_project/08_dev_step.md`: Step 3.2要件
- `.claude/02_backend/01_backend_api_routes.md`: APIエンドポイント仕様
- `.claude/04_ui/00_screen_design_overview.md`: UI設計
- `.claude/06_security/security_requirements.md`: セキュリティ要件
- `.claude/07_frontend/01_phase3_step1_backend_implementation_plan.md`: Step 3.1実装パターン

---

## 11. 注意事項

### 11.1 ソースコード未作成
この計画書は**実装計画のみ**です。実際のソースコードは作成していません。

### 11.2 段階的実装
複雑な機能は以下のように段階的に実装してください：

**Step 1（最小限の動作）**:
- ファイル選択 → プレビュー表示 → 取込実行 → 結果表示

**Step 2（エラーハンドリング追加）**:
- バリデーション、エラートースト、リトライ機構

**Step 3（UX向上）**:
- プログレッシブディスクロージャー、スムーズスクロール、ローディング表示

**Step 4（セキュリティ強化）**:
- CSRF対策、XSS対策、入力バリデーション

### 11.3 テスタビリティ
各機能が独立してテスト可能な設計になっています：
- ヘルパー関数は純粋関数（副作用なし）
- DOM操作関数は単一責任原則
- API連携は非同期処理の適切なハンドリング

### 11.4 保守性
- コード内コメント（日本語）を充実させる
- 関数は100行以内に収める
- グローバル変数を避け、即時関数で名前空間を分離

---

## 12. 実装完了チェックリスト

### 12.1 HTML実装
- [ ] `templates/index.html` 作成完了
- [ ] 5つのセクション実装完了
- [ ] Bootstrap 5.3クラス適用完了
- [ ] ARIA属性追加完了
- [ ] レスポンシブデザイン確認完了

### 12.2 JavaScript実装
- [ ] `static/js/index.js` 作成完了
- [ ] イベントリスナー設定完了
- [ ] ファイル選択処理実装完了
- [ ] プレビュー処理実装完了
- [ ] 取込実行処理実装完了
- [ ] ヘルパー関数実装完了

### 12.3 API連携
- [ ] POST /upload 連携完了
- [ ] POST /preview 連携完了
- [ ] POST /process 連携完了
- [ ] エラーハンドリング実装完了

### 12.4 セキュリティ
- [ ] CSRF対策実装完了（Meta+Fetchヘッダー方式）
- [ ] XSS対策実装完了（エスケープ処理）
- [ ] ファイルバリデーション実装完了
- [ ] 入力バリデーション実装完了

### 12.5 テスト
- [ ] UI操作テスト（10ケース）完了
- [ ] API連携テスト（8ケース）完了
- [ ] レスポンシブデザインテスト（3ケース）完了
- [ ] アクセシビリティテスト（4ケース）完了
- [ ] エラーハンドリングテスト（5ケース）完了
- [ ] セキュリティテスト（4ケース）完了

### 12.6 ドキュメント
- [ ] コード内コメント追加完了
- [ ] README更新（使用方法追加）
- [ ] 実装完了報告書作成

---

**実装計画作成完了日**: 2025-12-29
**次のステップ**: Phase 3 Step 3.2実装開始（templates/index.html作成）
