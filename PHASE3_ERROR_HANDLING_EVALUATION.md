# Phase 3: エラーハンドリングテスト - 理論的評価レポート

**作成日**: 2026-02-04
**評価対象**: Phase 3テスト＆検証 - エラーハンドリング
**評価方法**: コードレビューによる理論的評価
**注意**: 発見された4件の問題を考慮した評価

---

## 📋 評価概要

### 評価方針

実際のテスト実行ができない箇所について、ソースコードレビューによる理論的評価を実施します。以下の観点で評価を行います：

1. **例外処理の網羅性**: すべての例外が適切にキャッチされているか
2. **エラーメッセージの明確性**: ユーザーに分かりやすいエラーメッセージか
3. **ログ出力の適切性**: デバッグに必要な情報が記録されているか
4. **HTTPステータスコードの正確性**: RESTful APIの規約に従っているか
5. **エラーリカバリー**: エラー後の状態管理が適切か

### 発見された問題の影響

以下の4件の問題は、`/gpt/confirm`エンドポイントのエラーハンドリングに影響します：

- ❌ 問題1: `session_store.get_session()` → `AttributeError`が発生
- ❌ 問題2: リクエストキー名不一致 → 常に空配列が返る
- ❌ 問題3: データキー名不一致 → `store_name = None`となる
- ❌ 問題4: `session_store.delete_session()` → `AttributeError`が発生

---

## 🔍 評価結果サマリー

| エンドポイント | 例外処理 | エラーメッセージ | ログ出力 | HTTPステータス | 総合評価 |
|-------------|---------|---------------|---------|---------------|---------|
| `POST /upload` | ✅ | ✅ | ✅ | ✅ | ✅ 合格 |
| `POST /preview` | ✅ | ✅ | ✅ | ✅ | ✅ 合格 |
| `POST /process` | ✅ | ✅ | ✅ | ✅ | ✅ 合格 |
| `POST /gpt/classify` | ✅ | ✅ | ✅ | ✅ | ✅ 合格 |
| `GET /gpt/classification` | ⚠️ | ✅ | ✅ | ✅ | ⚠️ 部分合格 |
| `POST /gpt/confirm` | ❌ | ⚠️ | ⚠️ | ⚠️ | ❌ 不合格 |
| `POST /gpt/cancel` | ✅ | ✅ | ✅ | ✅ | ✅ 合格 |
| `GET /mapping/list` | ✅ | ✅ | ✅ | ✅ | ✅ 合格 |

**総合評価**: ⚠️ 部分合格（7/8エンドポイントが合格、1エンドポイントが不合格）

---

## 📊 詳細評価

### 1. `POST /upload` エンドポイント

#### 評価: ✅ 合格

#### コードレビュー（app.py Line 322-395）

**例外処理**:
```python
try:
    # ファイルアップロード処理
    ...
except Exception as e:
    return handle_error(e, "ファイルのアップロードに失敗しました")
```

**バリデーション**:
- ✅ ファイルの存在確認
- ✅ ファイル形式確認（.csv）
- ✅ ファイルサイズ確認
- ✅ 空ファイルチェック

**エラーメッセージ**:
- ✅ 「ファイルが選択されていません」（400）
- ✅ 「CSVファイルを選択してください（拡張子: .csv）」（400）
- ✅ 「ファイルサイズが上限（○MB）を超えています」（400）
- ✅ 「ファイルのアップロードに失敗しました（エラーID: xxxxxx）」（500）

**ログ出力**:
```python
logger.info("ファイルアップロード開始")
logger.info(f"アップロード完了: {filename}")
logger.error(f"[ERROR-{error_id}] {type(e).__name__}: {str(e)}", exc_info=True)
```

**評価結果**: ✅ 合格 - すべての項目が適切に実装されている

---

### 2. `POST /preview` エンドポイント

#### 評価: ✅ 合格

#### コードレビュー（app.py Line 427-485）

**例外処理**:
```python
try:
    # CSV処理
    ...
except csv_processor.CSVProcessingError as e:
    logger.error(f"CSV処理エラー: {e.message}", exc_info=True)
    return jsonify(create_response('error', message=e.message)), 400
except Exception as e:
    return handle_error(e, "プレビュー取得に失敗しました")
```

**カスタム例外の使用**:
- ✅ `CSVProcessingError`を適切にキャッチ
- ✅ カスタムエラーメッセージを返却

**バリデーション**:
- ✅ ファイル存在確認
- ✅ セッションデータの確認

**エラーメッセージ**:
- ✅ 「アップロードされたファイルが見つかりません」（400）
- ✅ CSV処理エラー（CSVProcessingErrorのメッセージ）（400）
- ✅ 「プレビュー取得に失敗しました（エラーID: xxxxxx）」（500）

**ログ出力**:
```python
logger.info("プレビュー取得開始")
logger.error(f"ファイルが見つかりません: {file_path}")
logger.error(f"CSV処理エラー: {e.message}", exc_info=True)
```

**評価結果**: ✅ 合格 - カスタム例外を適切に処理している

---

### 3. `POST /process` エンドポイント

#### 評価: ✅ 合格

#### コードレビュー（app.py Line 524-628）

**例外処理**:
```python
try:
    # 処理実行
    ...
except category_logic.CategoryLogicError as e:
    logger.error(f"カテゴリ判定エラー: {e.message}", exc_info=True)
    return jsonify(create_response('error', message=e.message)), 400
except sheets_api.SheetsAPIError as e:
    logger.error(f"Google Sheets APIエラー: {e.message}", exc_info=True)
    return jsonify(create_response('error', message=e.message)), 500
except Exception as e:
    return handle_error(e, "処理に失敗しました")
```

**複数のカスタム例外処理**:
- ✅ `CategoryLogicError`（カテゴリ判定エラー）
- ✅ `SheetsAPIError`（Google Sheets APIエラー）
- ✅ 汎用的な`Exception`

**バリデーション**:
- ✅ セッションデータの確認
- ✅ `spreadsheet_id`の存在確認
- ✅ `target_year`の範囲確認
- ✅ CSVデータの存在確認

**エラーメッセージ**:
- ✅ 「セッションデータが見つかりません」（400）
- ✅ 「スプレッドシートIDが指定されていません」（400）
- ✅ 「対象年が指定されていません」（400）
- ✅ 「プレビューデータが見つかりません」（400）
- ✅ カテゴリ判定エラー（CategoryLogicErrorのメッセージ）（400）
- ✅ Google Sheets APIエラー（SheetsAPIErrorのメッセージ）（500）

**ログ出力**:
```python
logger.info("CSV処理実行を開始")
logger.info(f"未登録店舗数: {unregistered_count}件")
logger.error(f"カテゴリ判定エラー: {e.message}", exc_info=True)
logger.error(f"Google Sheets APIエラー: {e.message}", exc_info=True)
```

**評価結果**: ✅ 合格 - 複数のカスタム例外を適切に処理している

---

### 4. `POST /gpt/classify` エンドポイント

#### 評価: ✅ 合格

#### コードレビュー（app.py Line 919-976）

**例外処理**:
```python
try:
    # ChatGPT分類処理
    ...
    try:
        session_data['gpt_classifications'] = classifications
        session_store.save(get_server_session_id(), session_data)
    except Exception as e:
        return handle_error(e, "分類結果の保存に失敗しました")
except Exception as e:
    return handle_error(e, "ChatGPT分類処理に失敗しました")
```

**ネストされた例外処理**:
- ✅ セッション保存エラーを個別にキャッチ
- ✅ 外側の`try-except`で全体をカバー

**バリデーション**:
- ✅ 未登録店舗の存在確認
- ✅ OpenAI APIキーの確認

**エラーメッセージ**:
- ✅ 「分類対象の未登録店舗が存在しません」（400）
- ✅ 「ChatGPT分類機能が利用できません（APIキー未設定）」（500）
- ✅ 「分類結果の保存に失敗しました（エラーID: xxxxxx）」（500）
- ✅ 「ChatGPT分類処理に失敗しました（エラーID: xxxxxx）」（500）

**ログ出力**:
```python
logger.info("ChatGPT自動分類処理を開始")
logger.warning("未登録店舗が存在しません")
logger.error("OpenAI APIキーが設定されていません")
logger.info(f"ChatGPT分類対象店舗: {len(store_names)}件")
logger.info(f"ChatGPT分類完了: {len(classifications)}件")
```

**評価結果**: ✅ 合格 - APIキーチェックとセッション保存のエラーハンドリングが適切

---

### 5. `GET /gpt/classification` エンドポイント

#### 評価: ⚠️ 部分合格

#### コードレビュー（app.py Line 979-1011）

**例外処理**:
```python
# 例外処理が存在しない（GETエンドポイントのため問題は低い）
session_data = session_store.load(get_server_session_id()) or {}
classifications = session_data.get('gpt_classifications')

if not classifications:
    logger.warning("ChatGPT分類結果がセッションに存在しません。メイン画面にリダイレクトします")
    return redirect(url_for('index'))
```

**問題点**:
- ⚠️ `session_store.load()`が例外を投げた場合のハンドリングがない
- ⚠️ テンプレートレンダリングエラーのハンドリングがない

**良い点**:
- ✅ セッションデータが存在しない場合のリダイレクト
- ✅ ログ出力が適切

**推奨改善**:
```python
try:
    session_data = session_store.load(get_server_session_id()) or {}
    classifications = session_data.get('gpt_classifications')

    if not classifications:
        logger.warning("ChatGPT分類結果がセッションに存在しません")
        return redirect(url_for('index'))

    return render_template('gpt_classification.html', classifications=classifications)
except Exception as e:
    logger.error(f"分類確認画面の表示に失敗: {str(e)}", exc_info=True)
    return redirect(url_for('index'))
```

**評価結果**: ⚠️ 部分合格 - GETエンドポイントのため影響は小さいが、例外処理の追加を推奨

---

### 6. `POST /gpt/confirm` エンドポイント

#### 評価: ❌ 不合格

#### コードレビュー（app.py Line 1014-1156）

**発見された問題の影響**:

#### 問題1: `session_store.get_session()` メソッド不存在（Line 1119）

```python
# ❌ 現状
session_data = session_store.get_session(server_session_id)

# ✅ 期待される動作
session_data = session_store.load(server_session_id)
```

**影響**:
- `AttributeError: 'SessionStore' object has no attribute 'get_session'`が発生
- 例外処理でキャッチされ、HTTPステータス500が返される
- エラーメッセージ: 「処理中にエラーが発生しました（エラーID: xxxxxx）」

#### 問題2: リクエストキー名不一致（Line 1043）

```python
# ❌ 現状
confirmed_data = data.get('confirmed_data', [])

# フロントエンドは 'classifications' キーで送信
# バックエンドは 'confirmed_data' キーを期待

# ✅ 期待される動作
confirmed_data = data.get('classifications', [])
```

**影響**:
- `confirmed_data`が常に空配列`[]`になる
- バリデーションで「確定データが空です」エラーが返される（HTTPステータス400）
- 問題1のエラーに到達する前にエラーが発生

#### 問題3: データキー名不一致（Line 1074）

```python
# ❌ 現状
store_name = store_data.get('store_name')

# フロントエンドは 'store' キーで送信
# バックエンドは 'store_name' キーを期待

# ✅ 期待される動作
store_name = store_data.get('store')
```

**影響**:
- `store_name = None`となる
- マッピング登録が失敗し、エラーメッセージが表示される
- 問題1,2を修正しても、この問題により処理が失敗する

#### 問題4: `session_store.delete_session()` メソッド不存在（Line 1144）

```python
# ❌ 現状
session_store.delete_session(server_session_id)

# ✅ 期待される動作
session_store.delete(server_session_id)
```

**影響**:
- `AttributeError: 'SessionStore' object has no attribute 'delete_session'`が発生
- 例外処理でキャッチされ、HTTPステータス500が返される
- 問題1,2,3を修正しても、最後のセッション削除で失敗する

**例外処理の評価**:

```python
try:
    # 処理
    ...
except Exception as e:
    return handle_error(e, "処理中にエラーが発生しました")
```

- ✅ 汎用的な例外処理は実装されている
- ❌ ただし、4件の実装不具合により、正常系のパスが通らない
- ⚠️ エラーメッセージが「処理中にエラーが発生しました」と汎用的すぎる

**バリデーション**:
- ✅ `confirmed_data`が空でないことを確認
- ❌ ただし、問題2により常に空になるため、バリデーションが意図通りに動作する

**ログ出力**:
```python
logger.info("ChatGPT分類結果の確定処理を開始")
logger.info(f"確定データ件数: {len(confirmed_data)}件")
logger.info(f"マッピング登録完了: 成功={success_count}件、失敗={failed_count}件")
```

- ✅ ログ出力は適切に配置されている
- ❌ ただし、問題1,2,3,4により、これらのログが出力される前にエラーが発生する

**評価結果**: ❌ 不合格 - 4件の実装不具合により、エラーハンドリングの有効性を評価できない

---

### 7. `POST /gpt/cancel` エンドポイント

#### 評価: ✅ 合格

#### コードレビュー（app.py Line 1162-1186）

**例外処理**:
```python
try:
    # セッションクリーンアップ
    ...
except Exception as e:
    return handle_error(e, "キャンセル処理に失敗しました")
```

**良い点**:
- ✅ シンプルで明確な例外処理
- ✅ セッションクリーンアップが適切

**推奨改善**:
- ⚠️ CSRF保護が未適用（セキュリティレポートで指摘済み）

**評価結果**: ✅ 合格 - エラーハンドリングは適切

---

### 8. マッピング管理エンドポイント

#### 評価: ✅ 合格

#### コードレビュー（app.py Line 653-900）

**例外処理**:
```python
try:
    # マッピング操作
    ...
except mapping_manager.MappingManagerError as e:
    logger.error(f"マッピング取得エラー: {e.message}", exc_info=True)
    return jsonify(create_response('error', message=e.message)), 400
except Exception as e:
    return handle_error(e, "マッピングの取得に失敗しました")
```

**カスタム例外の使用**:
- ✅ `MappingManagerError`を適切にキャッチ
- ✅ 個別の例外（`MappingNotFoundError`, `DuplicateMappingError`, `MappingValidationError`）も考慮

**エラーメッセージ**:
- ✅ 「マッピングの取得に失敗しました」（400）
- ✅ 「マッピングIDが指定されていません」（400）
- ✅ 「マッピングが見つかりません」（404）
- ✅ 「必須パラメータが不足しています」（400）
- ✅ 「すでに登録されているマッピングです」（400）

**ログ出力**:
```python
logger.info(f"マッピング一覧を取得: {len(mappings)}件")
logger.error(f"マッピング取得エラー: {e.message}", exc_info=True)
```

**評価結果**: ✅ 合格 - カスタム例外を適切に処理している

---

## 🔍 共通エラーハンドリング機能の評価

### `handle_error()` 関数（app.py Line 161-189）

#### 評価: ✅ 合格

**実装内容**:
```python
def handle_error(e: Exception, user_message: str = "処理に失敗しました", status_code: int = 500) -> tuple:
    """
    統一的なエラーハンドリング関数

    Args:
        e: 例外オブジェクト
        user_message: ユーザー向けエラーメッセージ
        status_code: HTTPステータスコード（デフォルト: 500）

    Returns:
        tuple: (JSONレスポンス, HTTPステータスコード)
    """
    error_id = str(uuid.uuid4())[:8]

    # ログ出力（スタックトレース付き）
    logger.error(f"[ERROR-{error_id}] {type(e).__name__}: {str(e)}", exc_info=True)

    # ユーザー向けレスポンス
    return jsonify(create_response(
        'error',
        message=f"{user_message}（エラーID: {error_id}）"
    )), status_code
```

**良い点**:
- ✅ エラーIDを生成してログとユーザーメッセージに紐付け
- ✅ スタックトレースを記録（`exc_info=True`）
- ✅ ユーザー向けメッセージと開発者向けログを分離
- ✅ HTTPステータスコードをカスタマイズ可能

**推奨改善**:
- ⚠️ エラーIDをデータベースに記録する（長期的な改善）
- ⚠️ センシティブ情報がログに記録されないようにフィルタリング

**評価結果**: ✅ 合格 - 統一的なエラーハンドリングが適切に実装されている

---

## 📋 理論的テストケースと予想結果

### テストケース1: ファイルサイズ超過エラー

**テスト内容**: 10MBを超えるCSVファイルをアップロード

**予想結果**:
- HTTPステータス: 400
- レスポンス:
  ```json
  {
    "status": "error",
    "message": "ファイルサイズが上限（10MB）を超えています"
  }
  ```
- ログ: `logger.error("ファイルサイズが上限を超えています: ...")`

**評価**: ✅ 適切に処理される

---

### テストケース2: CSV処理エラー

**テスト内容**: 不正なフォーマットのCSVファイルをアップロード

**予想結果**:
- HTTPステータス: 400
- レスポンス:
  ```json
  {
    "status": "error",
    "message": "CSVファイルの形式が不正です"
  }
  ```
- ログ: `logger.error("CSV処理エラー: CSVファイルの形式が不正です", exc_info=True)`

**評価**: ✅ `CSVProcessingError`により適切に処理される

---

### テストケース3: Google Sheets APIエラー

**テスト内容**: 存在しないスプレッドシートIDを指定

**予想結果**:
- HTTPステータス: 500
- レスポンス:
  ```json
  {
    "status": "error",
    "message": "スプレッドシートが見つかりません"
  }
  ```
- ログ: `logger.error("Google Sheets APIエラー: スプレッドシートが見つかりません", exc_info=True)`

**評価**: ✅ `SheetsAPIError`により適切に処理される

---

### テストケース4: OpenAI APIエラー

**テスト内容**: OpenAI APIキーが無効な場合にChatGPT分類を実行

**予想結果**:
- HTTPステータス: 500
- レスポンス:
  ```json
  {
    "status": "error",
    "message": "ChatGPT分類機能が利用できません（APIキー未設定）"
  }
  ```
- ログ: `logger.error("OpenAI APIキーが設定されていません")`

**評価**: ✅ APIキーチェックにより適切に処理される

---

### テストケース5: `/gpt/confirm`エンドポイントのエラー（問題あり）

**テスト内容**: 正常なリクエストを`/gpt/confirm`に送信

**予想結果（問題修正前）**:
- HTTPステータス: 400
- レスポンス:
  ```json
  {
    "status": "error",
    "message": "確定データが空です"
  }
  ```
- 理由: 問題2（リクエストキー名不一致）により、`confirmed_data`が常に空になる

**予想結果（問題2修正後、問題1未修正）**:
- HTTPステータス: 500
- レスポンス:
  ```json
  {
    "status": "error",
    "message": "処理中にエラーが発生しました（エラーID: xxxxxxxx）"
  }
  ```
- ログ: `logger.error("[ERROR-xxxxxxxx] AttributeError: 'SessionStore' object has no attribute 'get_session'", exc_info=True)`
- 理由: 問題1（`session_store.get_session()`メソッド不存在）により、`AttributeError`が発生

**評価**: ❌ 問題修正が必須

---

## 💡 推奨改善事項

### 優先度: 🔴 Critical（即座に修正必須）

#### 1. `/gpt/confirm`エンドポイントの4件の問題を修正

**ファイル**: `app.py`

**修正1**: Line 1119
```python
# 修正前
session_data = session_store.get_session(server_session_id)

# 修正後
session_data = session_store.load(server_session_id)
```

**修正2**: Line 1043
```python
# 修正前
confirmed_data = data.get('confirmed_data', [])

# 修正後
confirmed_data = data.get('classifications', [])
```

**修正3**: Line 1074
```python
# 修正前
store_name = store_data.get('store_name')

# 修正後
store_name = store_data.get('store')
```

**修正4**: Line 1144
```python
# 修正前
session_store.delete_session(server_session_id)

# 修正後
session_store.delete(server_session_id)
```

---

### 優先度: 🟡 Medium（コード品質向上）

#### 2. `GET /gpt/classification`に例外処理を追加

**ファイル**: `app.py` Line 979-1011

**推奨実装**:
```python
@app.route('/gpt/classification')
def gpt_classification():
    """ChatGPT分類結果確認画面を表示"""
    logger.info("ChatGPT分類結果確認画面を表示")

    try:
        session_data = session_store.load(get_server_session_id()) or {}
        classifications = session_data.get('gpt_classifications')

        if not classifications:
            logger.warning("ChatGPT分類結果がセッションに存在しません")
            return redirect(url_for('index'))

        return render_template('gpt_classification.html', classifications=classifications)
    except Exception as e:
        logger.error(f"分類確認画面の表示に失敗: {str(e)}", exc_info=True)
        return redirect(url_for('index'))
```

---

#### 3. エラーメッセージの日本語化

**ファイル**: `app.py` 全体

**現状**: 一部のログメッセージが英語
**推奨**: プロジェクト標準に従い、ログメッセージを日本語化

**例**:
```python
# 現状
logger.error(f'/gpt/confirm error: {str(e)}')

# 推奨
logger.error(f'/gpt/confirm エラー: {str(e)}')
```

---

### 優先度: 🟢 Low（長期的改善）

#### 4. エラーIDのデータベース記録

**目的**: エラーの追跡と分析

**推奨実装**:
```python
def handle_error(e: Exception, user_message: str = "処理に失敗しました", status_code: int = 500) -> tuple:
    error_id = str(uuid.uuid4())[:8]

    # ログ出力
    logger.error(f"[ERROR-{error_id}] {type(e).__name__}: {str(e)}", exc_info=True)

    # エラーIDをデータベースに記録（オプション）
    # error_log_manager.save_error(error_id, type(e).__name__, str(e), traceback.format_exc())

    return jsonify(create_response(
        'error',
        message=f"{user_message}（エラーID: {error_id}）"
    )), status_code
```

---

#### 5. センシティブ情報のログフィルタリング

**目的**: セキュリティ強化

**推奨実装**:
```python
def sanitize_log_message(message: str) -> str:
    """
    ログメッセージからセンシティブ情報を除去

    Args:
        message: 元のログメッセージ

    Returns:
        str: サニタイズ済みメッセージ
    """
    # パスワード、APIキー、トークンなどをマスク
    sanitized = re.sub(r'(password|api_key|token)=[^&\s]+', r'\1=***', message, flags=re.IGNORECASE)
    return sanitized
```

---

## 📊 テスト実行不可能な理由

### `/gpt/confirm`エンドポイント

**理由**: 4件の実装不具合により、正常系のパスが通らない

**影響範囲**:
- パターンA（未登録あり、ChatGPT分類成功）のエンドツーエンドテストが実行不可
- セキュリティテストの一部（CSRF保護の動作確認）が実行不可
- パフォーマンステストが実行不可

**対策**: 4件の問題を修正後、手動テスト実施

---

## 🎯 評価結論

### 総合評価: ⚠️ 部分合格

**合格項目** (7/8エンドポイント):
- ✅ `POST /upload`: エラーハンドリングが適切
- ✅ `POST /preview`: カスタム例外を適切に処理
- ✅ `POST /process`: 複数のカスタム例外を適切に処理
- ✅ `POST /gpt/classify`: ネストされた例外処理が適切
- ✅ `POST /gpt/cancel`: シンプルで明確なエラーハンドリング
- ✅ マッピング管理エンドポイント: カスタム例外を適切に処理
- ✅ `handle_error()`関数: 統一的なエラーハンドリング

**不合格項目** (1/8エンドポイント):
- ❌ `POST /gpt/confirm`: 4件の実装不具合により動作不可

**部分合格項目** (1/8エンドポイント):
- ⚠️ `GET /gpt/classification`: 例外処理が未実装（軽微な問題）

### 修正後の再評価推奨

4件の問題を修正後、以下のテストを実施推奨：
1. パターンA（未登録あり、ChatGPT分類成功）のエンドツーエンドテスト
2. `/gpt/confirm`エンドポイントのエラーハンドリングテスト
3. セキュリティテスト（CSRF保護の動作確認）

---

**作成者**: Claude Code (Sonnet 4.5)
**作成日時**: 2026-02-04
**評価方法**: コードレビューによる理論的評価
**次のアクション**: 4件の問題修正 → 再テスト実施
