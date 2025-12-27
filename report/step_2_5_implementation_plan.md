# Step 2.5: Flaskアプリケーション実装計画書

**作成日**: 2025-12-24
**対象**: `app.py` メインアプリケーション実装
**ステータス**: 実装前計画書

---

## 1. 概要

### 1.1 目的

Step 2.5では、イオンカード明細取込システムのメインアプリケーション（`app.py`）を実装します。これまでに完成した4つのバックエンドモジュール（CSV処理、カテゴリ判定、マッピング管理、Google Sheets API連携）を統合し、Web APIエンドポイントとして公開します。

### 1.2 実装対象

- **ファイル**: `app.py`
- **役割**: Flaskアプリケーション、ルート定義、エラーハンドリング、セッション管理
- **実装規模**: 約800-1000行（推定）

### 1.3 依存モジュール

以下の既存モジュールを使用します：

| モジュール | 用途 |
|----------|------|
| `modules/csv_processor.py` | CSVファイル読込、エンコーディング検出、データ抽出 |
| `modules/category_logic.py` | 店舗名カテゴリ判定、未登録店舗検出 |
| `modules/mapping_manager.py` | マッピングCRUD操作、データ永続化 |
| `modules/sheets_api.py` | Google Sheets認証・接続、セル更新 |
| `config.py` | アプリケーション設定クラス |

### 1.4 技術スタック

- **Webフレームワーク**: Flask 3.1.2+
- **セッション管理**: Flask組み込みセッション
- **テンプレートエンジン**: Jinja2
- **JSON処理**: Python標準ライブラリ
- **ロギング**: Python標準ライブラリ logging

---

## 2. Phase構成

Step 2.5は複雑な実装となるため、以下の5つのPhaseに分けて段階的に実装します。

| Phase | 内容 | 実装目安行数 |
|-------|------|------------|
| **Phase 1** | 基盤実装（Flask初期化、設定読込、基本ルート） | 150-200行 |
| **Phase 2** | CSVアップロード機能（upload、previewルート） | 200-250行 |
| **Phase 3** | CSV処理・Sheets連携（processルート、メインロジック） | 250-300行 |
| **Phase 4** | マッピング管理API（mapping関連ルート） | 150-200行 |
| **Phase 5** | エラーハンドリング・クリーンアップ（404/500、ファイル削除） | 150-200行 |

**合計推定**: 約900-1150行

---

## 3. Phase 1: 基盤実装

### 3.1 実装内容

#### 3.1.1 Flaskアプリケーション初期化

```python
from flask import Flask, render_template, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import os
import logging
from pathlib import Path
from datetime import datetime
import json

# プロジェクトモジュールのインポート
from modules import csv_processor
from modules import category_logic
from modules import mapping_manager
from modules import sheets_api
from config import config

# Flaskアプリケーション作成
app = Flask(__name__)

# 環境変数から環境名を取得（デフォルト: development）
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# アップロードフォルダの作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
```

#### 3.1.2 ロギング設定

```python
# ロガー設定
logging.basicConfig(
    level=getattr(logging, app.config['LOG_LEVEL']),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(app.config['LOG_FILE']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
```

#### 3.1.3 基本ルート実装

##### GET / - メイン画面

```python
@app.route('/')
def index():
    """
    メイン画面を表示

    Returns:
        str: index.htmlのレンダリング結果
    """
    logger.info("メイン画面を表示")
    return render_template('index.html')
```

##### GET /mapping - マッピング管理画面

```python
@app.route('/mapping')
def mapping():
    """
    マッピング管理画面を表示

    Returns:
        str: mapping.htmlのレンダリング結果
    """
    logger.info("マッピング管理画面を表示")
    return render_template('mapping.html')
```

##### GET /result - 処理結果画面

```python
@app.route('/result')
def result():
    """
    処理結果を表示

    セッションから処理結果を取得して表示します。
    結果が存在しない場合はメイン画面にリダイレクトします。

    Returns:
        str: result.htmlのレンダリング結果 または リダイレクト
    """
    logger.info("処理結果画面を表示")

    # セッションから処理結果を取得
    result_data = session.get('process_result')

    if result_data is None:
        logger.warning("処理結果がセッションに存在しません。メイン画面にリダイレクトします")
        return redirect(url_for('index'))

    return render_template('result.html', result=result_data)
```

### 3.2 ヘルパー関数

#### 3.2.1 ファイル拡張子チェック

```python
def allowed_file(filename: str) -> bool:
    """
    ファイルの拡張子が許可されているか確認

    Args:
        filename (str): ファイル名

    Returns:
        bool: 許可されている場合True

    Example:
        >>> allowed_file('data.csv')
        True
        >>> allowed_file('data.txt')
        False
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
```

#### 3.2.2 統一レスポンス形式

```python
def create_response(status: str, data=None, message: str = None) -> dict:
    """
    統一されたJSON形式のレスポンスを作成

    Args:
        status (str): レスポンスステータス（'success' または 'error'）
        data: レスポンスデータ（オプション）
        message (str): メッセージ（オプション）

    Returns:
        dict: レスポンス辞書

    Example:
        >>> create_response('success', data={'count': 10}, message='処理完了')
        {'status': 'success', 'data': {'count': 10}, 'message': '処理完了'}
    """
    response = {'status': status}

    if data is not None:
        response['data'] = data

    if message is not None:
        response['message'] = message

    return response
```

#### 3.2.3 古いファイルのクリーンアップ

```python
def cleanup_old_files(directory: str, max_age_hours: int = 24) -> int:
    """
    指定ディレクトリ内の古いファイルを削除

    Args:
        directory (str): 対象ディレクトリパス
        max_age_hours (int): 最大保存時間（時間単位、デフォルト24時間）

    Returns:
        int: 削除されたファイル数

    Example:
        >>> cleanup_old_files('uploads', max_age_hours=24)
        3
    """
    deleted_count = 0
    current_time = datetime.now()
    max_age_seconds = max_age_hours * 3600

    try:
        for file_path in Path(directory).glob('*'):
            if file_path.is_file():
                file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)

                if file_age.total_seconds() > max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"古いファイルを削除: {file_path.name}")

        if deleted_count > 0:
            logger.info(f"{deleted_count}件の古いファイルを削除しました")

        return deleted_count

    except Exception as e:
        logger.error(f"ファイルクリーンアップ中にエラーが発生: {str(e)}")
        return deleted_count
```

### 3.3 Phase 1 完了基準

- [ ] Flaskアプリケーションが起動する
- [ ] ログ出力が正常に動作する
- [ ] GET `/` でindex.htmlが表示される
- [ ] GET `/mapping` でmapping.htmlが表示される
- [ ] ヘルパー関数のテストが通る

---

## 4. Phase 2: CSVアップロード機能

### 4.1 POST /upload - CSVファイルアップロード

#### 4.1.1 実装内容

```python
@app.route('/upload', methods=['POST'])
def upload():
    """
    CSVファイルをアップロードして一時保存

    Request:
        - files['csv_file']: アップロードされたCSVファイル

    Returns:
        JSON: {
            'status': 'success',
            'data': {
                'filename': str,
                'file_path': str,
                'file_size': int
            },
            'message': str
        }

    Raises:
        400: ファイルが送信されていない、拡張子不正、サイズ超過
        500: ファイル保存エラー
    """
    logger.info("CSVファイルアップロード処理を開始")

    try:
        # 1. ファイルの存在確認
        if 'csv_file' not in request.files:
            logger.warning("ファイルが送信されていません")
            return jsonify(create_response(
                'error',
                message='ファイルが選択されていません'
            )), 400

        file = request.files['csv_file']

        # 2. ファイル名の確認
        if file.filename == '':
            logger.warning("ファイル名が空です")
            return jsonify(create_response(
                'error',
                message='ファイルが選択されていません'
            )), 400

        # 3. 拡張子チェック
        if not allowed_file(file.filename):
            logger.warning(f"許可されていない拡張子: {file.filename}")
            return jsonify(create_response(
                'error',
                message='CSVファイルのみアップロード可能です'
            )), 400

        # 4. ファイル名のサニタイズ
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"

        # 5. ファイル保存
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(file_path)

        # 6. ファイルサイズ取得
        file_size = os.path.getsize(file_path)

        # 7. セッションにファイルパスを保存
        session['uploaded_file_path'] = file_path
        session['uploaded_filename'] = filename

        logger.info(f"ファイルアップロード成功: {safe_filename} ({file_size} bytes)")

        # 8. 古いファイルのクリーンアップ（非同期的に実行）
        cleanup_old_files(app.config['UPLOAD_FOLDER'])

        return jsonify(create_response(
            'success',
            data={
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size
            },
            message='ファイルのアップロードに成功しました'
        ))

    except Exception as e:
        logger.error(f"ファイルアップロード中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'ファイルのアップロードに失敗しました: {str(e)}'
        )), 500
```

### 4.2 POST /preview - CSVプレビュー取得

#### 4.2.1 実装内容

```python
@app.route('/preview', methods=['POST'])
def preview():
    """
    アップロードされたCSVファイルのプレビューを取得

    セッションから前回アップロードされたファイルパスを取得し、
    CSV処理モジュールを使用して先頭5件のデータを返します。

    Returns:
        JSON: {
            'status': 'success',
            'data': {
                'preview': List[Dict],  # 先頭5件
                'total_count': int,
                'total_amount': int,
                'date_range': {
                    'start': str,
                    'end': str
                }
            },
            'message': str
        }

    Raises:
        400: ファイル未アップロード、ファイルが存在しない
        500: CSV処理エラー
    """
    logger.info("CSVプレビュー取得処理を開始")

    try:
        # 1. セッションからファイルパス取得
        file_path = session.get('uploaded_file_path')

        if not file_path:
            logger.warning("ファイルがアップロードされていません")
            return jsonify(create_response(
                'error',
                message='先にファイルをアップロードしてください'
            )), 400

        # 2. ファイルの存在確認
        if not os.path.exists(file_path):
            logger.error(f"ファイルが見つかりません: {file_path}")
            return jsonify(create_response(
                'error',
                message='アップロードされたファイルが見つかりません'
            )), 400

        # 3. CSV処理モジュールを使用してデータ取得
        result = csv_processor.process_csv_file(
            file_path,
            allowed_dir=app.config['UPLOAD_FOLDER']
        )

        logger.info(
            f"CSVプレビュー取得成功: "
            f"{result['total_count']}件, "
            f"合計{result['summary']['total_amount']:,}円"
        )

        # 4. セッションに全データを保存（後続のprocess処理用）
        session['csv_data'] = result['details']

        return jsonify(create_response(
            'success',
            data={
                'preview': result['preview'],
                'total_count': result['total_count'],
                'total_amount': result['summary']['total_amount'],
                'date_range': result['summary']['date_range']
            },
            message=f'{result["total_count"]}件の明細データを読み込みました'
        ))

    except csv_processor.CSVProcessingError as e:
        logger.error(f"CSV処理エラー: {e.message}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'CSVファイルの処理に失敗しました: {e.message}'
        )), 500

    except Exception as e:
        logger.error(f"プレビュー取得中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'プレビュー取得に失敗しました: {str(e)}'
        )), 500
```

### 4.3 Phase 2 完了基準

- [ ] POST `/upload` でCSVファイルがアップロードできる
- [ ] ファイルバリデーションが正常に動作する
- [ ] セッションにファイルパスが保存される
- [ ] POST `/preview` でプレビューデータが取得できる
- [ ] エラーハンドリングが適切に動作する

---

## 5. Phase 3: CSV処理・Sheets連携（メインロジック）

### 5.1 POST /process - CSV処理実行

#### 5.1.1 実装内容

```python
@app.route('/process', methods=['POST'])
def process():
    """
    CSVデータを処理してGoogle Sheetsに反映

    Request JSON:
        {
            'spreadsheet_id': str,
            'target_year': int
        }

    Returns:
        JSON: {
            'status': 'success',
            'data': {
                'summary': {
                    'total_amount': int,
                    'total_count': int,
                    'by_category': Dict[str, Dict],
                    'by_month': Dict[int, Dict]
                },
                'unregistered_stores': List[Dict],
                'updated_cells': int,
                'processing_time': float
            },
            'message': str
        }

    Raises:
        400: パラメータ不正、CSV未アップロード
        500: 処理エラー
    """
    logger.info("CSV処理・Sheets更新処理を開始")
    start_time = datetime.now()

    try:
        # 1. リクエストパラメータ取得
        request_data = request.get_json()

        if not request_data:
            logger.warning("リクエストボディが空です")
            return jsonify(create_response(
                'error',
                message='リクエストパラメータが不正です'
            )), 400

        spreadsheet_id = request_data.get('spreadsheet_id')
        target_year = request_data.get('target_year')

        # 2. パラメータバリデーション
        if not spreadsheet_id:
            logger.warning("スプレッドシートIDが指定されていません")
            return jsonify(create_response(
                'error',
                message='スプレッドシートIDを指定してください'
            )), 400

        if not target_year or not isinstance(target_year, int):
            logger.warning(f"対象年が不正です: {target_year}")
            return jsonify(create_response(
                'error',
                message='対象年を正しく指定してください'
            )), 400

        # 3. セッションからCSVデータ取得
        csv_data = session.get('csv_data')

        if not csv_data:
            logger.warning("CSVデータがセッションに存在しません")
            return jsonify(create_response(
                'error',
                message='先にCSVファイルをプレビューしてください'
            )), 400

        logger.info(f"処理対象: {len(csv_data)}件, スプレッドシートID: {spreadsheet_id}, 対象年: {target_year}")

        # 4. マッピングデータ読み込み
        mapping_data = category_logic.load_mapping_data(app.config['MAPPING_FILE'])

        # 5. カテゴリ判定（バッチ処理）
        enriched_data = category_logic.determine_categories_batch(csv_data, mapping_data)

        # 6. 未登録店舗検出
        unregistered_stores = category_logic.detect_unregistered_stores(csv_data, mapping_data)

        logger.info(f"カテゴリ判定完了: 未登録店舗 {len(unregistered_stores)}件")

        # 7. Google Sheets認証・接続
        client = sheets_api.authenticate(Path(app.config['SERVICE_ACCOUNT_FILE']))
        spreadsheet = sheets_api.open_spreadsheet(client, spreadsheet_id)
        worksheet = sheets_api.get_year_sheet(spreadsheet, target_year)

        logger.info(f"Googleスプレッドシート接続成功: {target_year}年シート")

        # 8. 更新データの集計（月・カテゴリ別）
        updates = []
        category_summary = {}
        month_summary = {}

        for record in enriched_data:
            month = record['month']
            category = record.get('category', DEFAULT_CATEGORY)
            column = record.get('column', DEFAULT_COLUMN)
            amount = record['amount']

            # バッチ更新用データ
            updates.append({
                'month': month,
                'column_letter': column,
                'amount': float(amount),
                'add_mode': True  # 加算モード
            })

            # カテゴリ別サマリー
            if category not in category_summary:
                category_summary[category] = {
                    'amount': 0,
                    'count': 0,
                    'column': column
                }
            category_summary[category]['amount'] += amount
            category_summary[category]['count'] += 1

            # 月別サマリー
            if month not in month_summary:
                month_summary[month] = {
                    'amount': 0,
                    'count': 0
                }
            month_summary[month]['amount'] += amount
            month_summary[month]['count'] += 1

        # 9. バッチ更新実行
        batch_result = sheets_api.batch_update_cells(worksheet, updates)

        logger.info(f"セル更新完了: {batch_result['updated_cells']}セル")

        # 10. 処理結果サマリー作成
        total_amount = sum(r['amount'] for r in enriched_data)
        total_count = len(enriched_data)
        processing_time = (datetime.now() - start_time).total_seconds()

        result_data = {
            'summary': {
                'total_amount': total_amount,
                'total_count': total_count,
                'by_category': category_summary,
                'by_month': month_summary
            },
            'unregistered_stores': unregistered_stores,
            'updated_cells': batch_result['updated_cells'],
            'processing_time': processing_time,
            'spreadsheet_id': spreadsheet_id,
            'target_year': target_year
        }

        # 11. セッションに処理結果を保存
        session['process_result'] = result_data

        logger.info(
            f"CSV処理完了: "
            f"{total_count}件, "
            f"合計{total_amount:,}円, "
            f"処理時間{processing_time:.2f}秒"
        )

        return jsonify(create_response(
            'success',
            data=result_data,
            message=f'{total_count}件の処理が完了しました'
        ))

    except category_logic.CategoryLogicError as e:
        logger.error(f"カテゴリ判定エラー: {e.message}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'カテゴリ判定に失敗しました: {e.message}'
        )), 500

    except sheets_api.SheetsAPIError as e:
        logger.error(f"Google Sheets APIエラー: {e.message}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'スプレッドシート更新に失敗しました: {e.message}'
        )), 500

    except Exception as e:
        logger.error(f"CSV処理中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'処理に失敗しました: {str(e)}'
        )), 500
```

### 5.2 Phase 3 完了基準

- [ ] POST `/process` でCSVデータが処理される
- [ ] カテゴリ判定が正常に動作する
- [ ] Google Sheetsへの更新が成功する
- [ ] 未登録店舗が正しく検出される
- [ ] セッションに処理結果が保存される
- [ ] サマリー情報が正しく集計される

---

## 6. Phase 4: マッピング管理API

### 6.1 GET /mapping/list - マッピング一覧取得

```python
@app.route('/mapping/list', methods=['GET'])
def mapping_list():
    """
    全マッピングエントリを取得

    Returns:
        JSON: {
            'status': 'success',
            'data': {
                'mappings': List[MappingEntry],
                'count': int
            },
            'message': str
        }

    Raises:
        500: マッピング取得エラー
    """
    logger.info("マッピング一覧取得処理を開始")

    try:
        # マッピングマネージャーを使用して全件取得
        mappings = mapping_manager.get_all_mappings()

        logger.info(f"マッピング一覧取得成功: {len(mappings)}件")

        return jsonify(create_response(
            'success',
            data={
                'mappings': mappings,
                'count': len(mappings)
            },
            message=f'{len(mappings)}件のマッピングを取得しました'
        ))

    except Exception as e:
        logger.error(f"マッピング一覧取得中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'マッピング一覧の取得に失敗しました: {str(e)}'
        )), 500
```

### 6.2 POST /mapping/add - マッピング追加

```python
@app.route('/mapping/add', methods=['POST'])
def mapping_add():
    """
    新規マッピングを追加

    Request JSON:
        {
            'pattern': str,
            'match_type': str,
            'category': str,
            'column': str,
            'priority': int,
            'note': str (optional)
        }

    Returns:
        JSON: {
            'status': 'success',
            'data': {
                'mapping': MappingEntry
            },
            'message': str
        }

    Raises:
        400: パラメータ不正、重複エラー
        500: 追加処理エラー
    """
    logger.info("マッピング追加処理を開始")

    try:
        # 1. リクエストデータ取得
        request_data = request.get_json()

        if not request_data:
            logger.warning("リクエストボディが空です")
            return jsonify(create_response(
                'error',
                message='リクエストパラメータが不正です'
            )), 400

        # 2. 必須フィールドの確認
        required_fields = ['pattern', 'match_type', 'category', 'column', 'priority']
        missing_fields = [f for f in required_fields if f not in request_data]

        if missing_fields:
            logger.warning(f"必須フィールド不足: {missing_fields}")
            return jsonify(create_response(
                'error',
                message=f'必須フィールドが不足しています: {", ".join(missing_fields)}'
            )), 400

        # 3. マッピング追加
        added_mapping = mapping_manager.add_mapping(request_data)

        logger.info(
            f"マッピング追加成功: "
            f"ID={added_mapping['id']}, "
            f"pattern={added_mapping['pattern']}, "
            f"category={added_mapping['category']}"
        )

        return jsonify(create_response(
            'success',
            data={'mapping': added_mapping},
            message='マッピングを追加しました'
        ))

    except mapping_manager.DuplicateMappingError as e:
        logger.warning(f"マッピング重複エラー: {e.message}")
        return jsonify(create_response(
            'error',
            message=f'同じパターンとマッチタイプの組み合わせが既に存在します'
        )), 400

    except Exception as e:
        logger.error(f"マッピング追加中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'マッピングの追加に失敗しました: {str(e)}'
        )), 500
```

### 6.3 PUT /mapping/edit/<id> - マッピング編集

```python
@app.route('/mapping/edit/<int:mapping_id>', methods=['PUT'])
def mapping_edit(mapping_id: int):
    """
    既存マッピングを更新

    Args:
        mapping_id (int): マッピングID

    Request JSON:
        {
            'pattern': str (optional),
            'match_type': str (optional),
            'category': str (optional),
            'column': str (optional),
            'priority': int (optional),
            'note': str (optional)
        }

    Returns:
        JSON: {
            'status': 'success',
            'data': {
                'mapping': MappingEntry
            },
            'message': str
        }

    Raises:
        400: パラメータ不正
        404: マッピングが見つからない
        500: 更新処理エラー
    """
    logger.info(f"マッピング更新処理を開始: ID={mapping_id}")

    try:
        # 1. リクエストデータ取得
        request_data = request.get_json()

        if not request_data:
            logger.warning("リクエストボディが空です")
            return jsonify(create_response(
                'error',
                message='更新データが指定されていません'
            )), 400

        # 2. マッピング更新
        updated_mapping = mapping_manager.update_mapping(mapping_id, request_data)

        logger.info(
            f"マッピング更新成功: "
            f"ID={updated_mapping['id']}, "
            f"pattern={updated_mapping['pattern']}"
        )

        return jsonify(create_response(
            'success',
            data={'mapping': updated_mapping},
            message='マッピングを更新しました'
        ))

    except mapping_manager.MappingNotFoundError as e:
        logger.warning(f"マッピングが見つかりません: ID={mapping_id}")
        return jsonify(create_response(
            'error',
            message=f'指定されたマッピングが見つかりません: ID={mapping_id}'
        )), 404

    except Exception as e:
        logger.error(f"マッピング更新中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'マッピングの更新に失敗しました: {str(e)}'
        )), 500
```

### 6.4 DELETE /mapping/delete/<id> - マッピング削除

```python
@app.route('/mapping/delete/<int:mapping_id>', methods=['DELETE'])
def mapping_delete(mapping_id: int):
    """
    マッピングを削除

    Args:
        mapping_id (int): マッピングID

    Returns:
        JSON: {
            'status': 'success',
            'data': {
                'deleted_id': int
            },
            'message': str
        }

    Raises:
        404: マッピングが見つからない
        500: 削除処理エラー
    """
    logger.info(f"マッピング削除処理を開始: ID={mapping_id}")

    try:
        # マッピング削除
        deleted_mapping = mapping_manager.delete_mapping(mapping_id)

        logger.info(
            f"マッピング削除成功: "
            f"ID={deleted_mapping['id']}, "
            f"pattern={deleted_mapping['pattern']}"
        )

        return jsonify(create_response(
            'success',
            data={'deleted_id': mapping_id},
            message='マッピングを削除しました'
        ))

    except mapping_manager.MappingNotFoundError as e:
        logger.warning(f"マッピングが見つかりません: ID={mapping_id}")
        return jsonify(create_response(
            'error',
            message=f'指定されたマッピングが見つかりません: ID={mapping_id}'
        )), 404

    except Exception as e:
        logger.error(f"マッピング削除中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'マッピングの削除に失敗しました: {str(e)}'
        )), 500
```

### 6.5 Phase 4 完了基準

- [ ] GET `/mapping/list` でマッピング一覧が取得できる
- [ ] POST `/mapping/add` でマッピングが追加できる
- [ ] PUT `/mapping/edit/<id>` でマッピングが更新できる
- [ ] DELETE `/mapping/delete/<id>` でマッピングが削除できる
- [ ] エラーハンドリングが適切に動作する

---

## 7. Phase 5: エラーハンドリング・クリーンアップ

### 7.1 エラーハンドラー実装

#### 7.1.1 404エラー

```python
@app.errorhandler(404)
def not_found_error(error):
    """
    404エラーハンドラー

    Args:
        error: エラーオブジェクト

    Returns:
        JSON: エラーレスポンス
    """
    logger.warning(f"404エラー: {request.url}")

    # JSONリクエストの場合
    if request.is_json or request.path.startswith('/api/'):
        return jsonify(create_response(
            'error',
            message='指定されたリソースが見つかりません'
        )), 404

    # HTMLリクエストの場合
    return render_template('404.html'), 404
```

#### 7.1.2 500エラー

```python
@app.errorhandler(500)
def internal_error(error):
    """
    500エラーハンドラー

    Args:
        error: エラーオブジェクト

    Returns:
        JSON: エラーレスポンス
    """
    logger.error(f"500エラー: {str(error)}", exc_info=True)

    # JSONリクエストの場合
    if request.is_json or request.path.startswith('/api/'):
        return jsonify(create_response(
            'error',
            message='サーバー内部エラーが発生しました'
        )), 500

    # HTMLリクエストの場合
    return render_template('500.html'), 500
```

#### 7.1.3 413エラー（ファイルサイズ超過）

```python
@app.errorhandler(413)
def request_entity_too_large(error):
    """
    413エラーハンドラー（ファイルサイズ超過）

    Args:
        error: エラーオブジェクト

    Returns:
        JSON: エラーレスポンス
    """
    logger.warning("ファイルサイズが上限を超えています")

    max_size_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)

    return jsonify(create_response(
        'error',
        message=f'ファイルサイズが上限({max_size_mb:.0f}MB)を超えています'
    )), 413
```

### 7.2 ファイルクリーンアップ処理

#### 7.2.1 アップロード後の自動削除

```python
@app.after_request
def cleanup_after_request(response):
    """
    リクエスト処理後のクリーンアップ処理

    Args:
        response: レスポンスオブジェクト

    Returns:
        response: 変更されていないレスポンスオブジェクト
    """
    # AUTO_DELETE_UPLOADSが有効な場合、古いファイルを削除
    if app.config.get('AUTO_DELETE_UPLOADS', True):
        try:
            cleanup_old_files(app.config['UPLOAD_FOLDER'], max_age_hours=24)
        except Exception as e:
            logger.error(f"ファイルクリーンアップ中にエラーが発生: {str(e)}")

    return response
```

#### 7.2.2 セッションクリア処理

```python
@app.route('/clear_session', methods=['POST'])
def clear_session():
    """
    セッションをクリアする

    アップロードされたファイルを削除し、セッションデータをクリアします。

    Returns:
        JSON: {
            'status': 'success',
            'message': str
        }
    """
    logger.info("セッションクリア処理を開始")

    try:
        # アップロードファイルの削除
        file_path = session.get('uploaded_file_path')
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"アップロードファイルを削除: {file_path}")

        # セッションクリア
        session.clear()

        logger.info("セッションクリア完了")

        return jsonify(create_response(
            'success',
            message='セッションをクリアしました'
        ))

    except Exception as e:
        logger.error(f"セッションクリア中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'セッションのクリアに失敗しました: {str(e)}'
        )), 500
```

### 7.3 ログダウンロード機能

```python
@app.route('/download/log', methods=['GET'])
def download_log():
    """
    処理ログをダウンロード

    セッションから処理結果を取得し、テキストファイルとして返します。

    Returns:
        file: ログファイル（text/plain）

    Raises:
        400: ログデータが存在しない
        500: ファイル生成エラー
    """
    logger.info("ログダウンロード処理を開始")

    try:
        # セッションから処理結果取得
        result_data = session.get('process_result')

        if not result_data:
            logger.warning("ログデータがセッションに存在しません")
            return jsonify(create_response(
                'error',
                message='ダウンロード可能なログが存在しません'
            )), 400

        # ログテキスト生成
        log_lines = [
            "=== イオンカード明細取込処理ログ ===",
            f"処理日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"スプレッドシートID: {result_data.get('spreadsheet_id', 'N/A')}",
            f"対象年: {result_data.get('target_year', 'N/A')}年",
            "",
            "=== 処理サマリー ===",
            f"総件数: {result_data['summary']['total_count']}件",
            f"総金額: {result_data['summary']['total_amount']:,}円",
            f"更新セル数: {result_data.get('updated_cells', 0)}セル",
            f"処理時間: {result_data.get('processing_time', 0):.2f}秒",
            "",
            "=== カテゴリ別サマリー ===",
        ]

        for category, data in result_data['summary']['by_category'].items():
            log_lines.append(
                f"  {category}: {data['amount']:,}円 ({data['count']}件) - 列{data['column']}"
            )

        log_lines.append("")
        log_lines.append("=== 月別サマリー ===")

        for month, data in sorted(result_data['summary']['by_month'].items()):
            log_lines.append(
                f"  {month}月: {data['amount']:,}円 ({data['count']}件)"
            )

        if result_data['unregistered_stores']:
            log_lines.append("")
            log_lines.append("=== 未登録店舗 ===")
            for store in result_data['unregistered_stores']:
                log_lines.append(
                    f"  {store['store']}: {store['total_amount']:,}円 ({store['count']}件)"
                )

        log_text = "\n".join(log_lines)

        # テキストファイルとして保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"process_log_{timestamp}.txt"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(log_text)

        logger.info(f"ログファイル生成成功: {filename}")

        # ファイル送信（ダウンロード後自動削除）
        return send_file(
            filepath,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"ログダウンロード中にエラーが発生: {str(e)}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'ログのダウンロードに失敗しました: {str(e)}'
        )), 500
```

### 7.4 Phase 5 完了基準

- [ ] 404/500エラーハンドラーが動作する
- [ ] ファイルクリーンアップが正常に動作する
- [ ] セッションクリア機能が動作する
- [ ] ログダウンロードが正常に動作する

---

## 8. セキュリティ要件

### 8.1 ファイルアップロードセキュリティ

1. **ファイル拡張子検証**
   - `allowed_file()` 関数で `.csv` のみ許可
   - 大文字小文字を区別しない検証

2. **ファイル名サニタイズ**
   - `secure_filename()` を使用してパストラバーサル攻撃を防止
   - タイムスタンプを付与してファイル名の一意性を保証

3. **ファイルサイズ制限**
   - `MAX_CONTENT_LENGTH` で10MB制限
   - 413エラーハンドラーで適切なエラーメッセージ

4. **ファイルパス検証**
   - `csv_processor.validate_file_path()` でディレクトリトラバーサル対策
   - `allowed_dir` パラメータで許可ディレクトリを制限

### 8.2 セッション管理セキュリティ

1. **セッションクッキー設定**
   - `SESSION_COOKIE_HTTPONLY = True`: XSS対策
   - `SESSION_COOKIE_SECURE = False`: ローカル環境（本番はTrue）
   - `PERMANENT_SESSION_LIFETIME = 30分`: セッションタイムアウト

2. **シークレットキー**
   - `SECRET_KEY` は環境変数から取得（本番環境）
   - 開発環境のみデフォルト値を使用

### 8.3 APIセキュリティ

1. **入力バリデーション**
   - すべてのリクエストパラメータを検証
   - 必須フィールドの存在確認
   - データ型の検証

2. **エラーメッセージ**
   - 機密情報（ファイルパス、スタックトレース）を含めない
   - ユーザーフレンドリーなメッセージに変換
   - 詳細なエラーはログに記録

3. **CORS対策**
   - ローカル環境のみアクセス許可
   - 本番環境では適切なCORS設定が必要

### 8.4 認証情報管理

1. **Google サービスアカウント**
   - `config/service_account.json` は `.gitignore` に追加
   - 環境変数またはボリュームマウントで配置

2. **スプレッドシートID**
   - ユーザー入力として受け取る
   - セッションに保存しない（リクエスト毎に指定）

---

## 9. エラーハンドリング戦略

### 9.1 エラー階層

```
Exception (Python標準)
├── CSVProcessingError (csv_processor.py)
│   ├── EncodingDetectionError
│   ├── InvalidFileFormatError
│   ├── DateConversionError
│   ├── DataExtractionError
│   └── PathValidationError
├── CategoryLogicError (category_logic.py)
│   ├── MappingLoadError
│   ├── MappingValidationError
│   ├── CategoryMatchError
│   └── InvalidMappingFormatError
├── MappingManagerError (mapping_manager.py)
│   ├── MappingNotFoundError
│   ├── DuplicateMappingError
│   └── MappingSaveError
└── SheetsAPIError (sheets_api.py)
    ├── AuthenticationError
    ├── SpreadsheetNotFoundError
    ├── SheetNotFoundError
    └── CellUpdateError
```

### 9.2 エラーハンドリングパターン

#### パターン1: モジュール固有エラー

```python
try:
    result = csv_processor.process_csv_file(file_path)
except csv_processor.CSVProcessingError as e:
    logger.error(f"CSV処理エラー: {e.message}", exc_info=True)
    return jsonify(create_response(
        'error',
        message=f'CSVファイルの処理に失敗しました: {e.message}'
    )), 500
```

#### パターン2: 汎用エラー

```python
except Exception as e:
    logger.error(f"予期しないエラーが発生: {str(e)}", exc_info=True)
    return jsonify(create_response(
        'error',
        message=f'処理に失敗しました: {str(e)}'
    )), 500
```

#### パターン3: バリデーションエラー

```python
if not spreadsheet_id:
    logger.warning("スプレッドシートIDが指定されていません")
    return jsonify(create_response(
        'error',
        message='スプレッドシートIDを指定してください'
    )), 400
```

### 9.3 HTTPステータスコード使用基準

| コード | 用途 | 例 |
|-------|------|---|
| 200 | 成功 | データ取得、更新成功 |
| 400 | クライアントエラー | パラメータ不正、バリデーションエラー |
| 404 | リソース未検出 | マッピングID不存在、ページ未検出 |
| 413 | ファイルサイズ超過 | 10MB超過 |
| 500 | サーバーエラー | 予期しないエラー、処理失敗 |

---

## 10. ログ記録方針

### 10.1 ログレベル

| レベル | 用途 | 例 |
|-------|------|---|
| **DEBUG** | 開発時デバッグ情報 | リクエストパラメータ詳細、中間データ |
| **INFO** | 通常処理の記録 | 処理開始/完了、件数、処理時間 |
| **WARNING** | 注意が必要な状況 | バリデーションエラー、データ不足 |
| **ERROR** | エラー発生 | 例外キャッチ、処理失敗 |
| **CRITICAL** | システム重大エラー | 認証失敗、設定ファイル不存在 |

### 10.2 ログフォーマット

```
%(asctime)s [%(levelname)s] %(name)s: %(message)s
```

**出力例**:
```
2025-12-24 10:15:32,123 [INFO] __main__: CSVファイルアップロード処理を開始
2025-12-24 10:15:32,456 [INFO] __main__: ファイルアップロード成功: 20251224_101532_meisai.csv (52480 bytes)
2025-12-24 10:15:35,789 [INFO] __main__: CSVプレビュー取得成功: 150件, 合計123,456円
```

### 10.3 ログ出力先

1. **ファイル**: `app.log` (設定で変更可能)
2. **標準出力**: コンソール（開発時デバッグ用）

### 10.4 ログメッセージガイドライン

#### アップロード処理

```python
logger.info("CSVファイルアップロード処理を開始")
logger.info(f"ファイルアップロード成功: {filename} ({file_size} bytes)")
logger.warning("ファイルが選択されていません")
logger.error(f"ファイルアップロード中にエラーが発生: {str(e)}", exc_info=True)
```

#### CSV処理

```python
logger.info("CSVプレビュー取得処理を開始")
logger.info(f"CSVプレビュー取得成功: {count}件, 合計{amount:,}円")
logger.error(f"CSV処理エラー: {e.message}", exc_info=True)
```

#### Google Sheets連携

```python
logger.info(f"処理対象: {len(data)}件, スプレッドシートID: {id}, 対象年: {year}")
logger.info(f"Googleスプレッドシート接続成功: {year}年シート")
logger.info(f"セル更新完了: {count}セル")
logger.error(f"Google Sheets APIエラー: {e.message}", exc_info=True)
```

#### マッピング管理

```python
logger.info("マッピング一覧取得処理を開始")
logger.info(f"マッピング一覧取得成功: {len(mappings)}件")
logger.info(f"マッピング追加成功: ID={id}, pattern={pattern}, category={category}")
logger.warning(f"マッピング重複エラー: {e.message}")
```

---

## 11. テスト計画（簡易版）

### 11.1 Phase別テスト項目

#### Phase 1: 基盤実装

| テスト項目 | 確認内容 | 合否 |
|----------|---------|------|
| アプリ起動 | `python app.py` で起動する | [ ] |
| ログ出力 | app.log にログが記録される | [ ] |
| GET / | index.html が表示される | [ ] |
| GET /mapping | mapping.html が表示される | [ ] |
| allowed_file() | .csv は True、.txt は False | [ ] |
| cleanup_old_files() | 24時間以上経過したファイルが削除される | [ ] |

#### Phase 2: CSVアップロード

| テスト項目 | 確認内容 | 合否 |
|----------|---------|------|
| POST /upload (正常) | CSVファイルがアップロードされる | [ ] |
| POST /upload (拡張子不正) | 400エラーが返る | [ ] |
| POST /upload (サイズ超過) | 413エラーが返る | [ ] |
| POST /preview (正常) | 先頭5件が返る | [ ] |
| POST /preview (未アップロード) | 400エラーが返る | [ ] |

#### Phase 3: CSV処理

| テスト項目 | 確認内容 | 合否 |
|----------|---------|------|
| POST /process (正常) | Google Sheetsが更新される | [ ] |
| POST /process (パラメータ不正) | 400エラーが返る | [ ] |
| POST /process (CSV未アップロード) | 400エラーが返る | [ ] |
| カテゴリ判定 | 店舗名から正しくカテゴリが判定される | [ ] |
| 未登録店舗検出 | 未登録店舗がリスト化される | [ ] |

#### Phase 4: マッピング管理

| テスト項目 | 確認内容 | 合否 |
|----------|---------|------|
| GET /mapping/list | 全マッピングが取得できる | [ ] |
| POST /mapping/add (正常) | マッピングが追加される | [ ] |
| POST /mapping/add (重複) | 400エラーが返る | [ ] |
| PUT /mapping/edit/<id> (正常) | マッピングが更新される | [ ] |
| PUT /mapping/edit/<id> (ID不存在) | 404エラーが返る | [ ] |
| DELETE /mapping/delete/<id> (正常) | マッピングが削除される | [ ] |

#### Phase 5: エラーハンドリング

| テスト項目 | 確認内容 | 合否 |
|----------|---------|------|
| 404エラー | 存在しないURLで404エラー | [ ] |
| 500エラー | サーバーエラー時に500エラー | [ ] |
| POST /clear_session | セッションがクリアされる | [ ] |
| GET /download/log | ログファイルがダウンロードされる | [ ] |

### 11.2 統合テスト

| テスト項目 | 確認内容 | 合否 |
|----------|---------|------|
| エンドツーエンド | アップロード → プレビュー → 処理 → 結果表示 | [ ] |
| マッピング追加 → CSV処理 | 新規マッピングが反映される | [ ] |
| セッション管理 | セッションデータが適切に保存・削除される | [ ] |

---

## 12. 実装スケジュール

### 12.1 Phase別実装時間（推定）

| Phase | 実装時間 | テスト時間 | 合計 |
|-------|---------|----------|------|
| Phase 1 | 2-3時間 | 1時間 | 3-4時間 |
| Phase 2 | 3-4時間 | 1-2時間 | 4-6時間 |
| Phase 3 | 4-5時間 | 2-3時間 | 6-8時間 |
| Phase 4 | 2-3時間 | 1時間 | 3-4時間 |
| Phase 5 | 2-3時間 | 1時間 | 3-4時間 |
| **合計** | **13-18時間** | **6-8時間** | **19-26時間** |

### 12.2 推奨実装順序

1. **Day 1**: Phase 1（基盤実装） + Phase 2（CSVアップロード機能）
2. **Day 2**: Phase 3（CSV処理・Sheets連携、最重要）
3. **Day 3**: Phase 4（マッピング管理API） + Phase 5（エラーハンドリング）
4. **Day 4**: 統合テスト、バグ修正、ドキュメント整備

---

## 13. 実装チェックリスト

### 13.1 コード品質チェック

- [ ] PEP 8 準拠（行長、インデント、命名規則）
- [ ] 全関数にdocstring記載（引数、戻り値、例外）
- [ ] 型ヒント使用（パラメータ、戻り値）
- [ ] ログ出力適切（INFO、WARNING、ERROR）
- [ ] エラーハンドリング完備（例外キャッチ、適切なメッセージ）
- [ ] セキュリティ要件遵守（ファイルバリデーション、セッション管理）

### 13.2 機能実装チェック

- [ ] 全11ルートが実装されている
- [ ] ヘルパー関数が3つ実装されている
- [ ] エラーハンドラーが3つ実装されている
- [ ] セッション管理が正常に動作する
- [ ] ファイルクリーンアップが動作する

### 13.3 テストチェック

- [ ] 各Phaseの完了基準を満たす
- [ ] 統合テストが通る
- [ ] エラーケースがテストされている
- [ ] パフォーマンステスト（1000件データ、30秒以内）

---

## 14. 参考資料

### 14.1 既存モジュール

- `modules/csv_processor.py`: 918行（実装済み）
- `modules/category_logic.py`: 600行（実装済み）
- `modules/mapping_manager.py`: 595行（実装済み）
- `modules/sheets_api.py`: 779行（実装済み）

### 14.2 設計ドキュメント

- `.claude/02_backend/01_backend_api_routes.md`: APIルート設計
- `.claude/02_backend/02_backend_modules_spec.md`: モジュール仕様
- `.claude/06_security/security_requirements.md`: セキュリティ要件
- `.claude/08_library/03_library_usage_examples.md`: Flask使用例

### 14.3 コーディングスタイル参照

既存モジュールから統一されたスタイル：

1. **docstring形式**: Google形式（Args、Returns、Raises、Example）
2. **カスタム例外**: モジュール別基底クラス + 詳細例外クラス
3. **ログ出力**: `logger.info()`, `logger.error()` 使用
4. **エラーメッセージ**: 日本語、ユーザーフレンドリー
5. **セクション区切り**: `# ==================== セクション名 ====================`

---

## 15. まとめ

本計画書は、Step 2.5「Flaskアプリケーション作成（app.py）」の詳細実装計画を記載したものです。5つのPhaseに分けて段階的に実装することで、リスクを最小化し、品質を確保します。

### 15.1 重要なポイント

1. **既存モジュールの活用**: 4つの完成済みモジュールを統合
2. **段階的実装**: Phase 1-5で段階的に機能追加
3. **セキュリティ重視**: ファイルバリデーション、セッション管理、エラーハンドリング
4. **ログ記録徹底**: 全処理でINFO/WARNING/ERRORログを記録
5. **テスト完備**: 各Phase完了基準 + 統合テスト

### 15.2 次のステップ

1. **Phase 1実装**: 基盤実装から開始
2. **Phase毎の検証**: 完了基準を満たしてから次のPhaseへ
3. **統合テスト**: 全Phase完了後にエンドツーエンドテスト
4. **ドキュメント更新**: README.md、CLAUDE.md更新

---

**計画書作成者**: Claude Code
**作成日**: 2025-12-24
**バージョン**: 1.0
