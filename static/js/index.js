/**
 * イオンカード明細取込システム - メイン画面JavaScript
 * Phase 3 Step 3.2
 */

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
  /**
   * イベントリスナーの初期化処理
   */
  function initializeEventListeners() {
    // ファイル選択イベント
    const csvFileInput = document.getElementById('csvFile');
    if (csvFileInput) {
      csvFileInput.addEventListener('change', handleFileSelect);
    }

    // プレビューボタンクリック
    const previewBtn = document.getElementById('previewBtn');
    if (previewBtn) {
      previewBtn.addEventListener('click', handlePreview);
    }

    // 取込実行ボタンクリック
    const executeBtn = document.getElementById('executeBtn');
    if (executeBtn) {
      executeBtn.addEventListener('click', handleExecute);
    }
  }

  // =========================================
  // ファイル選択ハンドラー
  // =========================================
  /**
   * ファイル選択時の処理
   * @param {Event} event - ファイル選択イベント
   */
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

  // =========================================
  // プレビューハンドラー
  // =========================================
  /**
   * プレビューボタンクリック時の処理
   */
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
        headers: {
          'X-CSRF-Token': window.getCsrfToken()
        },
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
          'Content-Type': 'application/json',
          'X-CSRF-Token': window.getCsrfToken()
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

  // =========================================
  // 取込実行ハンドラー
  // =========================================
  /**
   * 取込実行ボタンクリック時の処理
   */
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
          'Content-Type': 'application/json',
          'X-CSRF-Token': window.getCsrfToken()
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

      window.hideProgress();

      // パターンA/C: 未登録店舗あり
      if (result.status === 'needs_classification') {
        const unregisteredCount = result.unregistered_count || 0;

        // ユーザー確認ダイアログ
        const userConfirmed = confirm(
          `未登録店舗が${unregisteredCount}件あります。\n` +
          'ChatGPTで自動分類しますか？\n\n' +
          '※OpenAI APIキーが設定されている必要があります'
        );

        if (userConfirmed) {
          // パターンA: ChatGPT分類実行
          await executeChatGPTClassification();
        } else {
          // パターンC: ユーザー拒否
          showWarning(
            '未登録店舗があります。マッピング管理画面で登録してください。',
            result.unregistered_stores
          );
        }
      }
      // パターンB: 未登録0件、即座に成功
      else if (result.status === 'success') {
        if (result.redirect_url) {
          window.location.href = result.redirect_url;
        } else {
          window.showToast('#successToast', '取込処理が正常に完了しました');
        }
      }
      // エラーハンドリング
      else if (result.status === 'error') {
        window.showToast('#errorToast', result.message || '処理中にエラーが発生しました');
      }

    } catch (error) {
      window.hideProgress();
      console.error('Execute error:', error);
      window.showToast('#errorToast', error.message);
    }
  }

  // =========================================
  // ChatGPT分類実行
  // =========================================
  /**
   * ChatGPT分類を実行し、確認画面にリダイレクト
   */
  async function executeChatGPTClassification() {
    try {
      // ローディング表示
      window.showProgress();

      const response = await fetch('/gpt/classify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': window.getCsrfToken()
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'ChatGPT分類に失敗しました');
      }

      const result = await response.json();

      window.hideProgress();

      if (result.status === 'success') {
        // 確認画面へリダイレクト
        window.location.href = '/gpt/classification';
      } else {
        window.showToast('#errorToast', result.message || 'ChatGPT分類に失敗しました');
      }

    } catch (error) {
      window.hideProgress();
      console.error('executeChatGPTClassification error:', error);
      window.showToast('#errorToast', 'ChatGPT分類中にエラーが発生しました: ' + error.message);
    }
  }

  // =========================================
  // 警告表示（パターンC用）
  // =========================================
  /**
   * 未登録店舗がある場合の警告表示
   * @param {string} message - 警告メッセージ
   * @param {Array} unregisteredStores - 未登録店舗リスト
   */
  function showWarning(message, unregisteredStores) {
    // Toast表示
    window.showToast('#errorToast', message);

    // 未登録店舗リスト表示（resultArea内）
    if (unregisteredStores && unregisteredStores.length > 0) {
      displayUnregisteredStores(unregisteredStores);
      showSection('resultArea');

      // スムーズスクロール
      document.getElementById('resultArea').scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  }

  // =========================================
  // 未登録店舗リスト表示
  // =========================================
  /**
   * 未登録店舗リストを結果エリアに表示
   * @param {Array} unregisteredStores - 未登録店舗リスト
   */
  function displayUnregisteredStores(unregisteredStores) {
    const unregisteredList = document.getElementById('unregisteredStoresList');
    if (!unregisteredList) return;

    unregisteredList.innerHTML = '';

    unregisteredStores.forEach(function(store) {
      const li = document.createElement('li');
      li.className = 'mb-1';
      li.textContent = `${escapeHtml(store.store)} (${formatCurrency(store.total_amount)}, ${store.count}件)`;
      unregisteredList.appendChild(li);
    });

    // 未登録店舗セクション表示
    const unregisteredSection = document.getElementById('unregisteredStoresSection');
    if (unregisteredSection) {
      unregisteredSection.classList.remove('d-none');
    }
  }

  // =========================================
  // ヘルパー関数: ファイルバリデーション
  // =========================================
  /**
   * ファイルのバリデーション
   * @param {File} file - 検証対象のファイル
   * @returns {Object} { valid: boolean, message?: string }
   */
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

  // =========================================
  // ヘルパー関数: ファイルサイズフォーマット
  // =========================================
  /**
   * ファイルサイズを人間が読みやすい形式に変換
   * @param {number} bytes - バイト数
   * @returns {string} フォーマットされたファイルサイズ
   */
  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

  // =========================================
  // ヘルパー関数: 通貨フォーマット
  // =========================================
  /**
   * 金額を日本円形式にフォーマット
   * @param {number} amount - 金額
   * @returns {string} フォーマットされた金額文字列
   */
  function formatCurrency(amount) {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY'
    }).format(amount);
  }

  // =========================================
  // ヘルパー関数: プレビュー表示更新
  // =========================================
  /**
   * プレビューエリアの表示を更新
   * @param {Object} data - プレビューデータ
   */
  function updatePreviewDisplay(data) {
    // 統計情報更新
    document.getElementById('previewTotalCount').textContent = data.total_count;
    document.getElementById('previewTotalAmount').textContent = formatCurrency(data.total_amount);
    document.getElementById('previewDateRange').textContent =
      `${data.date_range.start} ～ ${data.date_range.end}`;

    // テーブル更新
    const tbody = document.getElementById('previewTableBody');
    tbody.innerHTML = '';

    data.preview.forEach(function(row) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHtml(row.date)}</td>
        <td>${escapeHtml(row.store)}</td>
        <td class="text-end">${formatCurrency(row.amount)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // =========================================
  // ヘルパー関数: 結果表示更新
  // =========================================
  /**
   * 結果エリアの表示を更新
   * @param {Object} data - 処理結果データ
   */
  function updateResultDisplay(data) {
    // サマリー情報更新
    document.getElementById('resultTotalCount').textContent = data.summary.total_count;
    document.getElementById('resultTotalAmount').textContent = formatCurrency(data.summary.total_amount);
    document.getElementById('resultProcessingTime').textContent =
      data.processing_time.toFixed(2);

    // 月別・カテゴリ別サマリーテーブル更新
    const summaryTbody = document.getElementById('resultSummaryTableBody');
    summaryTbody.innerHTML = '';

    Object.entries(data.summary.by_month).forEach(function([month, monthData]) {
      Object.entries(monthData.by_category).forEach(function([category, categoryData]) {
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

      data.unregistered_stores.forEach(function(store) {
        const li = document.createElement('li');
        li.textContent = `${escapeHtml(store.store)} (${formatCurrency(store.total_amount)}, ${store.count}件)`;
        unregisteredList.appendChild(li);
      });

      document.getElementById('unregisteredStoresSection').classList.remove('d-none');
    } else {
      document.getElementById('unregisteredStoresSection').classList.add('d-none');
    }
  }

  // =========================================
  // ヘルパー関数: セクション表示制御
  // =========================================
  /**
   * セクションを表示
   * @param {string} sectionId - セクションのID
   */
  function showSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
      section.classList.remove('d-none');
    }
  }

  /**
   * セクションを非表示
   * @param {string} sectionId - セクションのID
   */
  function hideSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
      section.classList.add('d-none');
    }
  }

  // =========================================
  // ヘルパー関数: XSS対策エスケープ
  // =========================================
  /**
   * HTMLエスケープ処理（XSS対策）
   * @param {string} text - エスケープ対象のテキスト
   * @returns {string} エスケープ済みテキスト
   */
  function escapeHtml(text) {
    if (text == null) {
      return '';
    }
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, function(m) { return map[m]; });
  }

})();
