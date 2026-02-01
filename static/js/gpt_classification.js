/**
 * ChatGPT分類確認画面用JavaScript
 *
 * 機能:
 * 1. カテゴリ変更→列番号の自動連動
 * 2. 行削除機能
 * 3. 確定処理（AJAX POST /gpt/confirm）
 * 4. キャンセル処理（AJAX POST /gpt/cancel）
 * 5. 分類件数のリアルタイム更新
 *
 * 依存ライブラリ: jQuery 3.7.1（base.htmlで読み込み済み）
 */

$(document).ready(function() {
  'use strict';

  // CSRFトークンをmeta要素から取得
  const csrfToken = $('meta[name="csrf-token"]').attr('content');

  // ==================== 機能1: カテゴリ変更→列番号の自動連動 ====================

  /**
   * カテゴリセレクトボックスの変更イベント
   * 選択されたカテゴリに対応する列番号を、同じ行の列セレクトボックスに自動設定
   */
  $('.category-select').on('change', function() {
    const $selectedOption = $(this).find('option:selected');
    const column = $selectedOption.data('column');

    if (column) {
      // 同じ行の列セレクトボックスの値を更新
      $(this).closest('tr').find('.column-select').val(column);
    } else {
      console.warn('カテゴリに対応する列番号が見つかりません:', $selectedOption.val());
    }
  });


  // ==================== 機能2: 行削除機能 ====================

  /**
   * 削除ボタンのクリックイベント
   * 該当する行をテーブルから削除し、分類件数を更新
   */
  $('.delete-btn').on('click', function() {
    const $row = $(this).closest('tr');
    const storeName = $row.data('store');

    // 確認ダイアログ（Bootstrap Modalを使わないシンプル版）
    if (confirm(`「${storeName}」を削除してもよろしいですか？`)) {
      $row.fadeOut(300, function() {
        $(this).remove();
        updateCount();
      });
    }
  });


  // ==================== 機能3: 確定処理 ====================

  /**
   * 確定ボタンのクリックイベント
   * 現在のテーブルデータをJSON形式で収集し、/gpt/confirmにPOST
   */
  $('#confirm-btn').on('click', function() {
    const classifications = [];

    // テーブルの各行からデータを収集
    $('#classificationTable tbody tr').each(function() {
      const $row = $(this);
      classifications.push({
        store: $row.data('store'),
        category: $row.find('.category-select').val(),
        column: $row.find('.column-select').val()
      });
    });

    // バリデーション: 登録対象が0件の場合
    if (classifications.length === 0) {
      alert('登録対象がありません。少なくとも1件以上の分類結果が必要です。');
      return;
    }

    // 確定確認ダイアログ
    if (!confirm(`${classifications.length}件の分類結果をマッピングに登録します。よろしいですか？`)) {
      return;
    }

    // ボタンを無効化＆ローディング表示
    const $confirmBtn = $(this);
    $confirmBtn.prop('disabled', true)
               .html('<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> 登録中...');

    // AJAX POST リクエスト
    $.ajax({
      url: '/gpt/confirm',
      method: 'POST',
      contentType: 'application/json',
      headers: { 'X-CSRFToken': csrfToken },
      data: JSON.stringify({ classifications: classifications }),
      timeout: 30000, // 30秒タイムアウト
      success: function(response) {
        if (response.status === 'success') {
          alert(response.message || '分類結果をマッピングに登録しました。');
          window.location.href = '/';
        } else {
          // サーバーエラー（status: 'error'）
          alert('エラー: ' + (response.message || '登録に失敗しました'));
          $confirmBtn.prop('disabled', false)
                     .html('<i class="bi bi-check-circle"></i> 確定して登録');
        }
      },
      error: function(xhr, status, error) {
        // HTTPエラー処理
        let errorMsg = '通信エラーが発生しました';

        if (xhr.status === 400) {
          errorMsg = xhr.responseJSON?.message || 'リクエストが不正です';
        } else if (xhr.status === 500) {
          errorMsg = 'サーバーエラーが発生しました';
        } else if (status === 'timeout') {
          errorMsg = 'リクエストがタイムアウトしました';
        }

        console.error('確定処理エラー:', {
          status: xhr.status,
          statusText: xhr.statusText,
          responseText: xhr.responseText,
          error: error
        });

        alert('エラー: ' + errorMsg);

        // ボタンを再度有効化
        $confirmBtn.prop('disabled', false)
                   .html('<i class="bi bi-check-circle"></i> 確定して登録');
      }
    });
  });


  // ==================== 機能4: キャンセル処理 ====================

  /**
   * キャンセルボタンのクリックイベント
   * セッションの分類結果をクリアし、メイン画面に戻る
   */
  $('#cancel-btn').on('click', function() {
    if (!confirm('ChatGPT分類をキャンセルしますか？\nこの操作は元に戻せません。')) {
      return;
    }

    // AJAX POST リクエスト
    $.ajax({
      url: '/gpt/cancel',
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      timeout: 10000,
      success: function(response) {
        // 成功時はメイン画面にリダイレクト
        window.location.href = '/';
      },
      error: function(xhr, status, error) {
        console.error('キャンセル処理エラー:', {
          status: xhr.status,
          statusText: xhr.statusText,
          error: error
        });

        alert('キャンセル処理に失敗しました。画面を再読み込みしてください。');
      }
    });
  });


  // ==================== 機能5: 分類件数のリアルタイム更新 ====================

  /**
   * テーブルの行数をカウントし、画面表示を更新
   */
  function updateCount() {
    const count = $('#classificationTable tbody tr').length;
    $('#classificationCount').text(count);

    // 件数が0になった場合の警告表示（オプション）
    if (count === 0) {
      $('#classificationTable tbody').html(
        '<tr><td colspan="6" class="text-center text-muted py-4">' +
        '<i class="bi bi-inbox"></i> 登録対象がありません' +
        '</td></tr>'
      );
      $('#confirm-btn').prop('disabled', true);
    }
  }


  // ==================== 初期化処理 ====================

  /**
   * ページロード時の初期化
   * - 分類件数の表示が正しいか確認
   */
  (function init() {
    const initialCount = $('#classificationTable tbody tr').length;
    console.log('ChatGPT分類確認画面の初期化完了。分類件数:', initialCount);

    // 件数が0の場合、確定ボタンを無効化
    if (initialCount === 0) {
      $('#confirm-btn').prop('disabled', true);
    }
  })();

});
