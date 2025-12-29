/**
 * イオンカード明細取込システム - メインJavaScript
 * Phase 3 Step 3.1
 */

(function() {
  'use strict';

  // =========================================
  // DOMContentLoaded後の初期化
  // =========================================
  document.addEventListener('DOMContentLoaded', function() {
    initializeToasts();
    initializeModals();
    initializeAlerts();
    initializeTooltips();
  });

  // =========================================
  // トースト通知の初期化
  // =========================================
  /**
   * トースト通知の初期化処理
   * すべてのトースト要素に対してBootstrap Toastインスタンスを作成
   */
  function initializeToasts() {
    // すべてのトースト要素を取得
    const toastElements = document.querySelectorAll('.toast');

    toastElements.forEach(function(toastEl) {
      // Bootstrap Toast インスタンス作成（自動表示は無効）
      new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 5000  // 5秒後に自動消去
      });
    });
  }

  // =========================================
  // モーダルダイアログの初期化
  // =========================================
  /**
   * モーダルダイアログの初期化処理
   * モーダル表示時に最初の入力要素にフォーカス
   */
  function initializeModals() {
    // すべてのモーダル要素を取得
    const modals = document.querySelectorAll('.modal');

    modals.forEach(function(modalEl) {
      // モーダル表示完了時のイベントリスナー
      modalEl.addEventListener('shown.bs.modal', function() {
        // モーダル内の最初の入力可能要素を取得
        const firstInput = modalEl.querySelector('input, select, textarea, button');
        if (firstInput) {
          firstInput.focus();
        }
      });
    });
  }

  // =========================================
  // アラートの自動消去設定
  // =========================================
  /**
   * アラートの自動消去設定
   * 5秒後に自動的にアラートを消去
   */
  function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert-dismissible');

    alerts.forEach(function(alert) {
      // 5秒後に自動消去
      setTimeout(function() {
        const closeButton = alert.querySelector('.btn-close');
        if (closeButton) {
          closeButton.click();
        }
      }, 5000);
    });
  }

  // =========================================
  // ツールチップの初期化
  // =========================================
  /**
   * ツールチップの初期化処理
   * data-bs-toggle="tooltip"属性を持つすべての要素を初期化
   */
  function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(
      document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );

    tooltipTriggerList.map(function(tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  // =========================================
  // グローバル関数: トースト通知表示
  // =========================================
  /**
   * トースト通知を表示するグローバル関数
   * @param {string} toastId - トーストのID（#successToast, #errorToast等）
   * @param {string} message - 表示するメッセージ（オプション）
   */
  window.showToast = function(toastId, message) {
    const toastEl = document.querySelector(toastId);
    if (!toastEl) {
      console.error('Toast element not found:', toastId);
      return;
    }

    // メッセージが指定されている場合は設定
    const toastBody = toastEl.querySelector('.toast-body');
    if (toastBody && message) {
      toastBody.textContent = message;
    }

    // トースト表示
    const toast = bootstrap.Toast.getOrCreateInstance(toastEl);
    toast.show();
  };

  // =========================================
  // グローバル関数: プログレスインジケーター表示
  // =========================================
  /**
   * プログレスインジケーターを表示
   */
  window.showProgress = function() {
    const progressEl = document.getElementById('progressIndicator');
    if (progressEl) {
      progressEl.classList.remove('d-none');
    }
  };

  /**
   * プログレスインジケーターを非表示
   */
  window.hideProgress = function() {
    const progressEl = document.getElementById('progressIndicator');
    if (progressEl) {
      progressEl.classList.add('d-none');
    }
  };

  // =========================================
  // グローバル関数: フォームバリデーション
  // =========================================
  /**
   * フォームバリデーションを実行
   * @param {HTMLFormElement} form - 検証対象のフォーム要素
   * @returns {boolean} - バリデーション結果（true: 成功, false: 失敗）
   */
  window.validateForm = function(form) {
    if (!form.checkValidity()) {
      form.classList.add('was-validated');
      return false;
    }
    return true;
  };

  // =========================================
  // グローバル関数: CSRFトークン取得
  // =========================================
  /**
   * CSRFトークンをメタタグから取得
   * @returns {string} CSRFトークン値（存在しない場合は空文字列）
   */
  window.getCsrfToken = function() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
  };

})();
