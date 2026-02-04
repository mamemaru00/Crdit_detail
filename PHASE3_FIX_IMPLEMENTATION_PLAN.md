# Phase 3: 問題修正実装計画

**作成日**: 2026-02-04
**Issue**: #46
**前提**: Phase 3テスト＆検証レポート（`PHASE3_TEST_VERIFICATION_REPORT.md`）

---

## 📋 修正対象の問題一覧

Phase 3テスト＆検証で発見された以下の4件の問題を修正します:

| 問題ID | 優先度 | 問題内容 | ファイル | 行番号 |
|--------|--------|----------|----------|--------|
| 1 | 🔴 Critical | `session_store.get_session()`メソッドが存在しない | app.py | 1119 |
| 2 | 🔴 Critical | リクエストキー名の不一致 (`confirmed_data` vs `classifications`) | app.py | 1043 |
| 3 | 🔴 Critical | データキー名の不一致 (`store_name` vs `store`) | app.py | 1074 |
| 4 | 🔴 Critical | セッション削除メソッド名の誤り (`delete_session()` vs `delete()`) | app.py | 1144 |

---

## 🔧 修正内容

### 修正1: `session_store.get_session()` → `session_store.load()`

**ファイル**: `app.py`
**行番号**: 1119

**修正前**:
```python
session_data = session_store.get_session(server_session_id)
```

**修正後**:
```python
session_data = session_store.load(server_session_id)
```

**理由**:
- `SessionStore`クラスには`get_session()`メソッドは存在しない
- 正しいメソッド名は`load()`
- `modules/session_store.py`で定義されている公開メソッド:
  - `load(session_id: str) -> Optional[dict]`
  - `save(session_id: str, data: dict) -> None`
  - `delete(session_id: str) -> None`
  - `prune_expired() -> int`

**影響範囲**:
- `/gpt/confirm`エンドポイントのみ

**テスト方法**:
- パターンA（未登録あり、ChatGPT分類成功）のテストケース1を実行
- 「確定」ボタンクリック時に500エラーが発生しないことを確認

---

### 修正2: リクエストキー名を`confirmed_data` → `classifications`

**ファイル**: `app.py`
**行番号**: 1043

**修正前**:
```python
data = request.get_json()
confirmed_data = data.get('confirmed_data', [])

if not confirmed_data:
    logger.warning("確定データが空です")
    return jsonify({
        'status': 'error',
        'message': '確定データが空です'
    }), 400
```

**修正後**:
```python
data = request.get_json()
confirmed_data = data.get('classifications', [])  # 'classifications'に統一

if not confirmed_data:
    logger.warning("確定データが空です")
    return jsonify({
        'status': 'error',
        'message': '確定データが空です'
    }), 400
```

**理由**:
- フロントエンド（`static/js/gpt_classification.js` Line 100）は`classifications`キーで送信している
- バックエンドは`confirmed_data`キーを期待していたため、常に空配列を受け取っていた
- フロントエンドの実装に合わせてバックエンドを修正する

**フロントエンドコード（参考）**:
```javascript
// static/js/gpt_classification.js Line 95-101
$.ajax({
  url: '/gpt/confirm',
  method: 'POST',
  contentType: 'application/json',
  headers: { 'X-CSRFToken': csrfToken },
  data: JSON.stringify({ classifications: classifications }),  // ← 'classifications'キー
  // ...
});
```

**影響範囲**:
- `/gpt/confirm`エンドポイントのみ

**テスト方法**:
- パターンA（未登録あり、ChatGPT分類成功）のテストケース1を実行
- 「確定」ボタンクリック時に400エラー「確定データが空です」が発生しないことを確認

---

### 修正3: データキー名を`store_name` → `store`

**ファイル**: `app.py`
**行番号**: 1074

**修正前**:
```python
for store_data in confirmed_data:
    store_name = store_data.get('store_name')
    category = store_data.get('category')
    column = category_to_column.get(category)

    if not column:
        failed_mappings.append({
            'store_name': store_name,
            'reason': f'無効なカテゴリ: {category}'
        })
        continue

    result = mapping_manager.add_mapping(
        store_name=store_name,
        column=column,
        priority=4,
        source='auto'
    )

    if result['success']:
        success_count += 1
    else:
        failed_mappings.append({
            'store_name': store_name,
            'reason': result.get('message', '不明なエラー')
        })
```

**修正後**:
```python
for store_data in confirmed_data:
    store_name = store_data.get('store')  # 'store'に統一
    category = store_data.get('category')
    column = category_to_column.get(category)

    if not column:
        failed_mappings.append({
            'store_name': store_name,
            'reason': f'無効なカテゴリ: {category}'
        })
        continue

    result = mapping_manager.add_mapping(
        store_name=store_name,
        column=column,
        priority=4,
        source='auto'
    )

    if result['success']:
        success_count += 1
    else:
        failed_mappings.append({
            'store_name': store_name,
            'reason': result.get('message', '不明なエラー')
        })
```

**理由**:
- フロントエンド（`static/js/gpt_classification.js` Line 72）は`store`キーで送信している
- バックエンドは`store_name`キーを期待していたため、`store_name = None`となっていた
- フロントエンドの実装に合わせてバックエンドを修正する

**フロントエンドコード（参考）**:
```javascript
// static/js/gpt_classification.js Line 69-76
$('#classificationTable tbody tr').each(function() {
  const $row = $(this);
  classifications.push({
    store: $row.data('store'),          // ← 'store'キー
    category: $row.find('.category-select').val(),
    column: $row.find('.column-select').val()
  });
});
```

**影響範囲**:
- `/gpt/confirm`エンドポイントのマッピング登録処理のみ

**テスト方法**:
- パターンA（未登録あり、ChatGPT分類成功）のテストケース1を実行
- 「確定」ボタンクリック時にマッピング登録が成功することを確認
- Google Sheetsに金額が正しく反映されることを確認

---

### 修正4: セッション削除メソッドを`delete_session()` → `delete()`

**ファイル**: `app.py`
**行番号**: 1144

**修正前**:
```python
# セッションクリア
session_store.delete_session(server_session_id)
```

**修正後**:
```python
# セッションクリア
session_store.delete(server_session_id)
```

**理由**:
- `SessionStore`クラスには`delete_session()`メソッドは存在しない
- 正しいメソッド名は`delete()`
- `modules/session_store.py`で定義されている公開メソッド:
  - `load(session_id: str) -> Optional[dict]`
  - `save(session_id: str, data: dict) -> None`
  - `delete(session_id: str) -> None`
  - `prune_expired() -> int`

**影響範囲**:
- `/gpt/confirm`エンドポイントの最終処理のみ

**テスト方法**:
- パターンA（未登録あり、ChatGPT分類成功）のテストケース1を実行
- 「確定」ボタンクリック後、セッションが正しくクリアされることを確認
- 処理完了後、トップ画面にリダイレクトされることを確認

---

## 📝 修正後の完全なコード（`/gpt/confirm`エンドポイント）

**ファイル**: `app.py`
**開始行**: 1009

```python
@app.route('/gpt/confirm', methods=['POST'])
@csrf.protect
def gpt_confirm():
    """
    ユーザー確認後、ChatGPT分類結果をSQLiteに一括登録し、Google Sheetsに反映

    Request JSON:
        {
            'classifications': [
                {
                    'store': str,
                    'category': str,
                    'column': str
                },
                ...
            ]
        }

    Returns:
        JSON: {
            'status': 'success',
            'redirect_url': str,
            'success_count': int,
            'message': str
        }

    Raises:
        400: パラメータ不正、セッションエラー
        500: データベース登録エラー、Sheets更新エラー
    """
    logger.info("ChatGPT分類確定処理を開始")

    try:
        # バリデーション
        data = request.get_json()
        confirmed_data = data.get('classifications', [])  # ✅ 修正2: 'classifications'に統一

        if not confirmed_data:
            logger.warning("確定データが空です")
            return jsonify({
                'status': 'error',
                'message': '確定データが空です'
            }), 400

        # Step 1: SQLiteマッピング登録
        logger.info(f"マッピング登録開始: {len(confirmed_data)}件")
        success_count = 0
        failed_mappings = []

        # カテゴリ→列番号変換テーブル（正しいマッピング）
        category_to_column = {
            '食材費': 'C',
            '外食費': 'D',
            '自己投資費': 'E',
            '書籍代': 'F',
            '家電': 'G',
            '雑貨費': 'H',
            '衣服・化粧費': 'I',
            '娯楽': 'J',
            '旅行費': 'K',
            '通信費': 'O',
            '個人娯楽': 'R',
            'サブスク': 'T'
        }

        for store_data in confirmed_data:
            store_name = store_data.get('store')  # ✅ 修正3: 'store'に統一
            category = store_data.get('category')
            column = category_to_column.get(category)

            if not column:
                failed_mappings.append({
                    'store_name': store_name,
                    'reason': f'無効なカテゴリ: {category}'
                })
                continue

            result = mapping_manager.add_mapping(
                store_name=store_name,
                column=column,
                priority=4,
                source='auto'
            )

            if result['success']:
                success_count += 1
            else:
                failed_mappings.append({
                    'store_name': store_name,
                    'reason': result.get('message', '不明なエラー')
                })

        # 失敗がある場合はエラーレスポンス
        if failed_mappings:
            logger.warning(f"マッピング登録失敗: {len(failed_mappings)}件")
            return jsonify({
                'status': 'error',
                'message': f'{len(failed_mappings)}件のマッピング登録に失敗しました',
                'failed_mappings': failed_mappings
            }), 400

        logger.info(f"マッピング登録完了: {success_count}件")

        # Step 2: Google Sheets更新
        server_session_id = session.get('server_session_id')
        if not server_session_id:
            return jsonify({
                'status': 'error',
                'message': 'セッションが無効です'
            }), 400

        session_data = session_store.load(server_session_id)  # ✅ 修正1: load()に変更
        if not session_data:
            return jsonify({
                'status': 'error',
                'message': 'セッションデータが見つかりません'
            }), 400

        csv_data = session_data.get('csv_data', [])
        target_year = session_data.get('target_year', datetime.now().year)
        spreadsheet_id = os.getenv('SPREADSHEET_ID')

        logger.info("再カテゴリ判定開始（新規マッピングを反映）")

        # 再度カテゴリ判定（新規マッピングを反映）
        from modules.category_logic import categorize_data
        categorized_data, monthly_aggregation, _ = categorize_data(csv_data, mapping_manager)

        logger.info("Google Sheets更新開始")

        # Sheets更新
        sheets_api.batch_update_cells(spreadsheet_id, target_year, monthly_aggregation)

        logger.info("Google Sheets更新完了")

        # セッションクリア
        session_store.delete(server_session_id)  # ✅ 修正4: delete()に変更

        # Step 3: トップ画面リダイレクト
        return jsonify({
            'status': 'success',
            'redirect_url': '/?message=success',
            'success_count': success_count,
            'message': '取込処理が完了しました'
        }), 200

    except Exception as e:
        logger.error(f'/gpt/confirm エラー: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': '処理中にエラーが発生しました'
        }), 500
```

---

## ✅ 修正完了後のテスト計画

### テストケース1: パターンA（未登録あり、ChatGPT分類成功）

**前提条件**:
- Docker環境が起動している（`docker-compose up`）
- OpenAI APIキーが設定されている（`.env`ファイル）
- テスト用CSV（未登録店舗を含む）が用意されている

**手順**:
1. ブラウザで`http://localhost:5000/`にアクセス
2. スプレッドシートIDと対象年を入力
3. 未登録店舗を含むCSVをアップロード
4. 「取込実行」ボタンをクリック
5. 確認ダイアログ「未登録店舗が○件あります。ChatGPTで自動分類しますか？」が表示されることを確認
6. 「OK」をクリック
7. ローディング表示「ChatGPTで分類中...」が表示されることを確認
8. ChatGPT分類確認画面（`/gpt/classification`）にリダイレクトされることを確認
9. 分類結果が一覧表示されることを確認
10. カテゴリを手修正（オプション）
11. 「確定」ボタンをクリック
12. トップ画面（`/?message=success`）にリダイレクトされることを確認
13. Bootstrap Toastで「取込処理が正常に完了しました」が表示されることを確認
14. Google Sheetsに金額が正しく反映されているか確認
15. SQLiteマッピングDBに登録されているか確認（`source='auto'`, `priority=4`）

**期待結果**:
- すべての手順がエラーなく完了 ✅
- Google Sheetsに正しい金額が加算されている ✅
- マッピングDBに新規登録されている ✅

---

### テストケース2: パターンB（未登録なし）

**前提条件**:
- Docker環境が起動している
- テスト用CSV（全て登録済みの店舗）が用意されている

**手順**:
1. ブラウザで`http://localhost:5000/`にアクセス
2. スプレッドシートIDと対象年を入力
3. 全て登録済みの店舗を含むCSVをアップロード
4. 「取込実行」ボタンをクリック
5. 確認ダイアログが表示されず、即座にトップ画面にリダイレクトされることを確認
6. Bootstrap Toastで「取込処理が正常に完了しました」が表示されることを確認
7. Google Sheetsに金額が正しく反映されているか確認

**期待結果**:
- 確認ダイアログなし ✅
- 即座に完了 ✅
- Google Sheetsに正しい金額が加算されている ✅

---

### テストケース3: パターンC（ユーザー拒否）

**前提条件**:
- Docker環境が起動している
- テスト用CSV（未登録店舗を含む）が用意されている

**手順**:
1. ブラウザで`http://localhost:5000/`にアクセス
2. スプレッドシートIDと対象年を入力
3. 未登録店舗を含むCSVをアップロード
4. 「取込実行」ボタンをクリック
5. 確認ダイアログ「未登録店舗が○件あります。ChatGPTで自動分類しますか？」が表示されることを確認
6. 「キャンセル」をクリック
7. Toast表示「未登録店舗があります。マッピング管理画面で登録してください。」が表示されることを確認
8. 未登録店舗リストが表示されることを確認
9. Google Sheetsが更新されていないことを確認

**期待結果**:
- 警告メッセージが表示される ✅
- 未登録店舗リストが表示される ✅
- Google Sheetsは更新されない ✅

---

## 🚀 修正実装手順

### 手順1: コードの修正

```bash
# エディタでapp.pyを開く
code C:\work\Lesson\個人開発\Crdit_detail\app.py

# 以下の4箇所を修正:
# Line 1043: confirmed_data = data.get('classifications', [])
# Line 1074: store_name = store_data.get('store')
# Line 1119: session_data = session_store.load(server_session_id)
# Line 1144: session_store.delete(server_session_id)
```

---

### 手順2: 構文チェック

```bash
cd "C:\work\Lesson\個人開発\Crdit_detail"
python -m py_compile app.py
```

**期待結果**: エラーなし

---

### 手順3: Docker再起動

```bash
cd "C:\work\Lesson\個人開発\Crdit_detail"
docker-compose restart
```

**期待結果**: `aeon-card-nginx`と`aeon-card-import-system`が正常に再起動

---

### 手順4: 手動テスト実施

上記のテストケース1-3を実行し、すべてのケースが正常動作することを確認

---

## 📊 修正完了後の期待結果

| 項目 | 修正前 | 修正後 |
|------|--------|--------|
| パターンA（未登録あり、ChatGPT分類成功） | ❌ 500エラー | ✅ 正常動作 |
| パターンB（未登録なし） | ✅ 正常動作 | ✅ 正常動作 |
| パターンC（ユーザー拒否） | ✅ 正常動作 | ✅ 正常動作 |
| エラーハンドリング | ⚠️ 部分合格 | ✅ 合格 |
| セキュリティテスト | ⚠️ 部分合格 | ✅ 合格 |

---

## 作成者

- **Claude Code** (Sonnet 4.5)
- **作成日時**: 2026-02-04
- **プロジェクト**: イオンカード明細取込システム
- **バージョン**: v2.0（ChatGPT分類機能）

---

## 参考資料

- `PHASE3_TEST_VERIFICATION_REPORT.md` - Phase 3テスト＆検証レポート
- `.claude/02_backend/01_backend_api_routes.md` - バックエンドAPI仕様
- `modules/session_store.py` - SessionStoreクラス定義
- `static/js/gpt_classification.js` - ChatGPT分類確認画面JavaScript
- `CLAUDE.md` - プロジェクト実装ガイドライン
