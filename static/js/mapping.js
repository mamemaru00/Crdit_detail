/**
 * マッピング管理画面用JavaScript
 *
 * 店舗カテゴリマッピングの管理機能を提供します。
 * - マッピング一覧の表示・検索
 * - 新規マッピングの追加
 * - 既存マッピングの編集・削除
 * - CSRF保護対応
 *
 * @author Claude Code
 * @version 1.0
 * @created 2025-01-08
 */

// ==================== グローバル変数 ====================

// 全マッピングデータ（APIから取得）
let allMappings = [];

// 現在表示中のマッピングデータ（検索フィルタ適用後）
let filteredMappings = [];

// ページング設定
const ITEMS_PER_PAGE = 10;
let currentPage = 1;

// 編集中のマッピングID
let editingMappingId = null;

// ==================== 初期化処理 ====================

$(document).ready(function() {
  console.log('マッピング管理画面を初期化中...');

  // マッピング一覧を取得
  loadMappings();

  // イベントリスナー設定
  setupEventListeners();
});

// ==================== イベントリスナー設定 ====================

/**
 * 各種イベントリスナーを設定
 */
function setupEventListeners() {
  // 検索入力（リアルタイムフィルタリング）
  $('#searchInput').on('input', function() {
    filterMappings($(this).val());
  });

  // 検索クリアボタン
  $('#clearSearchBtn').on('click', function() {
    $('#searchInput').val('');
    filterMappings('');
  });

  // 新規追加ボタン（ヘッダー）
  $('#addMappingBtn').on('click', function() {
    showAddForm();
  });

  // 新規追加ボタン（データなし時）
  $('#addFirstMappingBtn').on('click', function() {
    showAddForm();
  });

  // 新規追加フォーム - 送信
  $('#addMappingForm').on('submit', function(e) {
    e.preventDefault();
    handleAddMapping();
  });

  // 新規追加フォーム - キャンセル
  $('#cancelAddBtn').on('click', function() {
    hideAddForm();
  });

  // 編集フォーム - 送信
  $('#editMappingForm').on('submit', function(e) {
    e.preventDefault();
    handleEditMapping();
  });

  // 編集フォーム - キャンセル
  $('#cancelEditBtn').on('click', function() {
    hideEditForm();
  });

  // 削除確認モーダル - 削除ボタン
  $('#confirmDeleteBtn').on('click', function() {
    handleDeleteMapping();
  });

  // カテゴリ選択時に列番号を自動設定
  $('#categorySelect').on('change', function() {
    autoSelectColumn('add', $(this).val());
  });

  $('#editCategorySelect').on('change', function() {
    autoSelectColumn('edit', $(this).val());
  });
}

// ==================== マッピング一覧取得 ====================

/**
 * マッピング一覧をAPIから取得
 */
function loadMappings() {
  console.log('マッピング一覧を取得中...');

  // ローディング表示
  showLoading();

  $.ajax({
    url: '/mapping/list',
    method: 'GET',
    dataType: 'json',
    timeout: 10000
  })
  .done(function(response) {
    console.log('マッピング一覧取得成功:', response);

    if (response.status === 'success') {
      allMappings = response.data.mappings || [];
      filteredMappings = [...allMappings];

      // テーブル描画
      renderTable();

      // 件数表示更新
      updateCountDisplay();

      // データの有無に応じた表示切り替え
      if (allMappings.length === 0) {
        showNoDataMessage();
      } else {
        showTableContainer();
      }
    } else {
      showErrorToast('マッピング一覧の取得に失敗しました: ' + (response.message || '不明なエラー'));
      showNoDataMessage();
    }
  })
  .fail(function(xhr, status, error) {
    console.error('マッピング一覧取得エラー:', status, error);

    let errorMessage = 'マッピング一覧の取得に失敗しました';

    if (xhr.status === 0) {
      errorMessage = 'サーバーに接続できません';
    } else if (xhr.status === 404) {
      errorMessage = 'マッピング一覧が見つかりません';
    } else if (xhr.status === 500) {
      errorMessage = 'サーバーエラーが発生しました';
    }

    showErrorToast(errorMessage);
    showNoDataMessage();
  })
  .always(function() {
    hideLoading();
  });
}

// ==================== 検索・フィルタリング ====================

/**
 * マッピング一覧を店舗名でフィルタリング
 *
 * @param {string} searchText - 検索文字列
 */
function filterMappings(searchText) {
  const lowerSearchText = searchText.toLowerCase().trim();

  if (lowerSearchText === '') {
    // 検索文字列が空の場合は全件表示
    filteredMappings = [...allMappings];
  } else {
    // 店舗名パターンで部分一致検索
    filteredMappings = allMappings.filter(mapping => {
      return mapping.pattern.toLowerCase().includes(lowerSearchText);
    });
  }

  // ページを先頭に戻す
  currentPage = 1;

  // テーブル再描画
  renderTable();

  // 件数表示更新
  updateCountDisplay();
}

// ==================== テーブル描画 ====================

/**
 * マッピングテーブルを描画
 */
function renderTable() {
  const tbody = $('#mappingTableBody');
  tbody.empty();

  // ページング計算
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, filteredMappings.length);
  const pageData = filteredMappings.slice(startIndex, endIndex);

  // データが0件の場合
  if (pageData.length === 0) {
    const noResultRow = $('<tr>');
    const noResultCell = $('<td colspan="4" class="text-center text-muted py-4">');
    noResultCell.text('検索条件に一致するマッピングがありません');
    noResultRow.append(noResultCell);
    tbody.append(noResultRow);

    // ページング非表示
    $('#paginationContainer').addClass('d-none');
    return;
  }

  // 各行を描画
  pageData.forEach(mapping => {
    const row = createMappingRow(mapping);
    tbody.append(row);
  });

  // ページング描画
  renderPagination();
  $('#paginationContainer').removeClass('d-none');
}

/**
 * マッピング行要素を作成
 *
 * @param {Object} mapping - マッピングデータ
 * @returns {jQuery} 行要素
 */
function createMappingRow(mapping) {
  const row = $('<tr>');

  // 店舗名パターン列
  const storeNameCell = $('<td>');
  storeNameCell.text(mapping.pattern);
  row.append(storeNameCell);

  // カテゴリ列
  const categoryCell = $('<td>');
  categoryCell.text(mapping.category);
  row.append(categoryCell);

  // 列番号列
  const columnCell = $('<td>');
  columnCell.text(mapping.column + '列');
  row.append(columnCell);

  // 操作列
  const actionsCell = $('<td>');

  // 編集ボタン
  const editBtn = $('<button type="button" class="btn btn-sm btn-warning me-2">');
  editBtn.html('<i class="bi bi-pencil"></i> 編集');
  editBtn.attr('aria-label', mapping.pattern + 'を編集');
  editBtn.on('click', function() {
    showEditForm(mapping);
  });
  actionsCell.append(editBtn);

  // 削除ボタン
  const deleteBtn = $('<button type="button" class="btn btn-sm btn-danger">');
  deleteBtn.html('<i class="bi bi-trash"></i> 削除');
  deleteBtn.attr('aria-label', mapping.pattern + 'を削除');
  deleteBtn.attr('data-mapping-id', mapping.id);
  deleteBtn.attr('data-store-name', mapping.pattern);
  deleteBtn.attr('data-bs-toggle', 'modal');
  deleteBtn.attr('data-bs-target', '#deleteConfirmModal');
  deleteBtn.on('click', function() {
    prepareDeleteModal(mapping);
  });
  actionsCell.append(deleteBtn);

  row.append(actionsCell);

  return row;
}

// ==================== ページング ====================

/**
 * ページネーションを描画
 */
function renderPagination() {
  const pagination = $('#pagination');
  pagination.empty();

  const totalPages = Math.ceil(filteredMappings.length / ITEMS_PER_PAGE);

  // ページが1ページのみの場合は非表示
  if (totalPages <= 1) {
    $('#paginationContainer').addClass('d-none');
    return;
  }

  // 前へボタン
  const prevLi = $('<li class="page-item">');
  if (currentPage === 1) {
    prevLi.addClass('disabled');
  }
  const prevLink = $('<a class="page-link" href="#" aria-label="前へ">');
  prevLink.html('<span aria-hidden="true">&laquo;</span>');
  prevLink.on('click', function(e) {
    e.preventDefault();
    if (currentPage > 1) {
      currentPage--;
      renderTable();
    }
  });
  prevLi.append(prevLink);
  pagination.append(prevLi);

  // ページ番号ボタン
  for (let i = 1; i <= totalPages; i++) {
    const pageLi = $('<li class="page-item">');
    if (i === currentPage) {
      pageLi.addClass('active');
    }
    const pageLink = $('<a class="page-link" href="#">');
    pageLink.text(i);
    pageLink.on('click', function(e) {
      e.preventDefault();
      currentPage = i;
      renderTable();
    });
    pageLi.append(pageLink);
    pagination.append(pageLi);
  }

  // 次へボタン
  const nextLi = $('<li class="page-item">');
  if (currentPage === totalPages) {
    nextLi.addClass('disabled');
  }
  const nextLink = $('<a class="page-link" href="#" aria-label="次へ">');
  nextLink.html('<span aria-hidden="true">&raquo;</span>');
  nextLink.on('click', function(e) {
    e.preventDefault();
    if (currentPage < totalPages) {
      currentPage++;
      renderTable();
    }
  });
  nextLi.append(nextLink);
  pagination.append(nextLi);
}

// ==================== 新規追加フォーム ====================

/**
 * 新規追加フォームを表示
 */
function showAddForm() {
  // フォームをリセット
  $('#addMappingForm')[0].reset();
  $('#addMappingForm').removeClass('was-validated');

  // フォームエリアを表示
  $('#addFormArea').removeClass('d-none');

  // 編集フォームを非表示
  hideEditForm();

  // スムーズスクロール
  $('html, body').animate({
    scrollTop: $('#addFormArea').offset().top - 100
  }, 500);
}

/**
 * 新規追加フォームを非表示
 */
function hideAddForm() {
  $('#addFormArea').addClass('d-none');
  $('#addMappingForm').removeClass('was-validated');
}

/**
 * 新規マッピング追加処理
 */
function handleAddMapping() {
  const form = $('#addMappingForm')[0];

  // バリデーションチェック
  if (!form.checkValidity()) {
    form.classList.add('was-validated');
    return;
  }

  // フォームデータ取得
  const formData = {
    pattern: $('#storeNameInput').val().trim(),
    match_type: 'contains',
    category: $('#categorySelect').val(),
    column: $('#columnSelect').val()
  };

  console.log('マッピング追加リクエスト:', formData);

  // ボタン無効化
  $('#submitAddBtn').prop('disabled', true);

  // AJAX送信
  $.ajax({
    url: '/mapping/add',
    method: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(formData),
    headers: {
      'X-CSRF-Token': getCsrfToken()
    },
    dataType: 'json',
    timeout: 10000
  })
  .done(function(response) {
    console.log('マッピング追加成功:', response);

    if (response.status === 'success') {
      showSuccessToast('マッピングを追加しました');

      // フォームを非表示
      hideAddForm();

      // 一覧を再読込
      loadMappings();
    } else {
      showErrorToast('マッピングの追加に失敗しました: ' + (response.message || '不明なエラー'));
    }
  })
  .fail(function(xhr, status, error) {
    console.error('マッピング追加エラー:', status, error);

    let errorMessage = 'マッピングの追加に失敗しました';

    if (xhr.status === 400) {
      const response = xhr.responseJSON;
      errorMessage = response ? response.message : 'リクエストパラメータが不正です';
    } else if (xhr.status === 0) {
      errorMessage = 'サーバーに接続できません';
    } else if (xhr.status === 500) {
      errorMessage = 'サーバーエラーが発生しました';
    }

    showErrorToast(errorMessage);
  })
  .always(function() {
    // ボタン有効化
    $('#submitAddBtn').prop('disabled', false);
  });
}

// ==================== 編集フォーム ====================

/**
 * 編集フォームを表示
 *
 * @param {Object} mapping - 編集対象マッピング
 */
function showEditForm(mapping) {
  // フォームをリセット
  $('#editMappingForm').removeClass('was-validated');

  // フォームにデータを設定
  $('#editMappingId').val(mapping.id);
  $('#editStoreNameInput').val(mapping.pattern);
  $('#editCategorySelect').val(mapping.category);
  $('#editColumnSelect').val(mapping.column);

  // 編集中IDを保存
  editingMappingId = mapping.id;

  // フォームエリアを表示
  $('#editFormArea').removeClass('d-none');

  // 新規追加フォームを非表示
  hideAddForm();

  // スムーズスクロール
  $('html, body').animate({
    scrollTop: $('#editFormArea').offset().top - 100
  }, 500);
}

/**
 * 編集フォームを非表示
 */
function hideEditForm() {
  $('#editFormArea').addClass('d-none');
  $('#editMappingForm').removeClass('was-validated');
  editingMappingId = null;
}

/**
 * マッピング編集処理
 */
function handleEditMapping() {
  const form = $('#editMappingForm')[0];

  // バリデーションチェック
  if (!form.checkValidity()) {
    form.classList.add('was-validated');
    return;
  }

  const mappingId = $('#editMappingId').val();

  // フォームデータ取得
  const formData = {
    pattern: $('#editStoreNameInput').val().trim(),
    match_type: 'contains',
    category: $('#editCategorySelect').val(),
    column: $('#editColumnSelect').val()
  };

  console.log('マッピング編集リクエスト:', mappingId, formData);

  // ボタン無効化
  $('#submitEditBtn').prop('disabled', true);

  // AJAX送信
  $.ajax({
    url: `/mapping/edit/${mappingId}`,
    method: 'PUT',
    contentType: 'application/json',
    data: JSON.stringify(formData),
    headers: {
      'X-CSRF-Token': getCsrfToken()
    },
    dataType: 'json',
    timeout: 10000
  })
  .done(function(response) {
    console.log('マッピング編集成功:', response);

    if (response.status === 'success') {
      showSuccessToast('マッピングを更新しました');

      // フォームを非表示
      hideEditForm();

      // 一覧を再読込
      loadMappings();
    } else {
      showErrorToast('マッピングの更新に失敗しました: ' + (response.message || '不明なエラー'));
    }
  })
  .fail(function(xhr, status, error) {
    console.error('マッピング編集エラー:', status, error);

    let errorMessage = 'マッピングの更新に失敗しました';

    if (xhr.status === 400) {
      const response = xhr.responseJSON;
      errorMessage = response ? response.message : 'リクエストパラメータが不正です';
    } else if (xhr.status === 404) {
      errorMessage = '指定されたマッピングが見つかりません';
    } else if (xhr.status === 0) {
      errorMessage = 'サーバーに接続できません';
    } else if (xhr.status === 500) {
      errorMessage = 'サーバーエラーが発生しました';
    }

    showErrorToast(errorMessage);
  })
  .always(function() {
    // ボタン有効化
    $('#submitEditBtn').prop('disabled', false);
  });
}

// ==================== 削除機能 ====================

/**
 * 削除確認モーダルを準備
 *
 * @param {Object} mapping - 削除対象マッピング
 */
function prepareDeleteModal(mapping) {
  // モーダルに店舗名を表示
  $('#deleteStoreName').text(mapping.pattern);

  // 削除ボタンにデータ属性を設定
  $('#confirmDeleteBtn').attr('data-mapping-id', mapping.id);
}

/**
 * マッピング削除処理
 */
function handleDeleteMapping() {
  const mappingId = $('#confirmDeleteBtn').attr('data-mapping-id');

  if (!mappingId) {
    showErrorToast('削除対象のマッピングIDが不正です');
    return;
  }

  console.log('マッピング削除リクエスト:', mappingId);

  // ボタン無効化
  $('#confirmDeleteBtn').prop('disabled', true);

  // AJAX送信
  $.ajax({
    url: `/mapping/delete/${mappingId}`,
    method: 'DELETE',
    headers: {
      'X-CSRF-Token': getCsrfToken()
    },
    dataType: 'json',
    timeout: 10000
  })
  .done(function(response) {
    console.log('マッピング削除成功:', response);

    if (response.status === 'success') {
      showSuccessToast('マッピングを削除しました');

      // モーダルを閉じる
      const modal = bootstrap.Modal.getInstance($('#deleteConfirmModal')[0]);
      modal.hide();

      // 一覧を再読込
      loadMappings();
    } else {
      showErrorToast('マッピングの削除に失敗しました: ' + (response.message || '不明なエラー'));
    }
  })
  .fail(function(xhr, status, error) {
    console.error('マッピング削除エラー:', status, error);

    let errorMessage = 'マッピングの削除に失敗しました';

    if (xhr.status === 404) {
      errorMessage = '指定されたマッピングが見つかりません';
    } else if (xhr.status === 0) {
      errorMessage = 'サーバーに接続できません';
    } else if (xhr.status === 500) {
      errorMessage = 'サーバーエラーが発生しました';
    }

    showErrorToast(errorMessage);
  })
  .always(function() {
    // ボタン有効化
    $('#confirmDeleteBtn').prop('disabled', false);
  });
}

// ==================== UI表示制御 ====================

/**
 * ローディング表示
 */
function showLoading() {
  $('#loadingIndicator').removeClass('d-none');
  $('#mappingTableContainer').addClass('d-none');
  $('#noDataMessage').addClass('d-none');
}

/**
 * ローディング非表示
 */
function hideLoading() {
  $('#loadingIndicator').addClass('d-none');
}

/**
 * テーブルコンテナを表示
 */
function showTableContainer() {
  $('#mappingTableContainer').removeClass('d-none');
  $('#noDataMessage').addClass('d-none');
}

/**
 * データなしメッセージを表示
 */
function showNoDataMessage() {
  $('#mappingTableContainer').addClass('d-none');
  $('#noDataMessage').removeClass('d-none');
}

/**
 * 件数表示を更新
 */
function updateCountDisplay() {
  $('#displayCount').text(filteredMappings.length);
  $('#totalCount').text(allMappings.length);
}

// ==================== ユーティリティ関数 ====================

/**
 * カテゴリに対応する列番号を自動選択
 *
 * @param {string} formType - 'add' または 'edit'
 * @param {string} category - カテゴリ名
 */
function autoSelectColumn(formType, category) {
  // カテゴリと列番号のマッピング
  const categoryColumnMap = {
    '支払額': 'B',
    '外食費': 'C',
    '日用品費': 'D',
    '美容費': 'E',
    '衣類費': 'F',
    '娯楽費': 'G',
    'ガソリン代': 'H',
    '医療費': 'I',
    '書籍費': 'J',
    '雑費': 'K',
    '教育費': 'L',
    '旅行費': 'M',
    '交通費': 'N',
    '通信費': 'O',
    '保険料': 'P',
    '税金': 'Q',
    '光熱費': 'R',
    '家賃': 'S',
    '駐車場代': 'T',
    'その他固定費': 'U',
    '予備': 'V'
  };

  const column = categoryColumnMap[category];

  if (column) {
    if (formType === 'add') {
      $('#columnSelect').val(column);
    } else if (formType === 'edit') {
      $('#editColumnSelect').val(column);
    }
  }
}

/**
 * CSRFトークンを取得
 *
 * @returns {string} CSRFトークン
 */
function getCsrfToken() {
  return $('meta[name="csrf-token"]').attr('content');
}

/**
 * 成功トーストを表示
 *
 * @param {string} message - メッセージ
 */
function showSuccessToast(message) {
  const toast = $('#successToast');
  toast.find('.toast-body').text(message);

  const bsToast = new bootstrap.Toast(toast[0], {
    delay: 3000
  });
  bsToast.show();
}

/**
 * エラートーストを表示
 *
 * @param {string} message - メッセージ
 */
function showErrorToast(message) {
  const toast = $('#errorToast');
  toast.find('.toast-body').text(message);

  const bsToast = new bootstrap.Toast(toast[0], {
    delay: 5000
  });
  bsToast.show();
}
