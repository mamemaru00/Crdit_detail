"""
イオンカード明細取込システム - メインアプリケーション

このモジュールは、イオンカード利用明細CSVファイルを取り込み、
Googleスプレッドシートに自動反映するFlaskアプリケーションです。

主な機能:
- CSVファイルアップロード・解析
- カテゴリ自動判定
- Google Sheets API連携
- マッピング管理

Author: Claude Code
Created: 2025-12-24
Version: 1.0
"""

from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
import os
import logging
from pathlib import Path
from datetime import datetime
import json
import uuid

# プロジェクトモジュールのインポート
from modules import csv_processor
from modules import category_logic
from modules import mapping_manager
from modules import sheets_api
from config import config

# ==================== アプリケーション初期化 ====================

# Flaskアプリケーション作成
app = Flask(__name__)

# 環境変数から環境名を取得（デフォルト: development）
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# CSRF保護の初期化
csrf = CSRFProtect(app)

# アップロードフォルダの作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 必要なディレクトリを自動作成
os.makedirs(Path(app.config['LOG_FILE']).parent, exist_ok=True)
os.makedirs('data/backups', exist_ok=True)

# SessionStore初期化
from modules.session_store import SessionStore

# セッションディレクトリ作成
os.makedirs(Path(app.config['SESSION_DB_PATH']).parent, exist_ok=True)

# ==================== ロギング設定 ====================

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

# SessionStoreインスタンス生成
session_store = SessionStore(
    db_path=app.config['SESSION_DB_PATH'],
    ttl_seconds=app.config['SESSION_TTL_SECONDS']
)

logger.info(f"SessionStore初期化完了: {app.config['SESSION_DB_PATH']}")

# ==================== 定数定義 ====================

# デフォルトカテゴリと列（未登録店舗用）
DEFAULT_CATEGORY = '支払額'
DEFAULT_COLUMN = 'B'

# ==================== ヘルパー関数 ====================

def get_server_session_id() -> str:
    """
    サーバーサイドセッションIDを取得または生成する

    Flask標準のsecure cookie sessionにserver_session_idを保存し、
    SessionStoreで大容量データを管理するためのキーとして使用する。

    Returns:
        str: 32文字のhex形式のセッションID

    Example:
        >>> session_id = get_server_session_id()
        >>> len(session_id)
        32
    """
    if 'server_session_id' not in session:
        session['server_session_id'] = uuid.uuid4().hex
        logger.debug(f"新しいserver_session_id生成: {session['server_session_id']}")
    return session['server_session_id']

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


def handle_error(e: Exception, user_message: str = "処理に失敗しました", status_code: int = 500) -> tuple:
    """
    統一エラーレスポンスヘルパー（情報漏洩対策）

    例外の詳細情報をログに記録し、ユーザーには安全なメッセージのみを返します。
    エラーIDを生成して、ログとユーザーメッセージを紐付けます。

    Args:
        e (Exception): 発生した例外
        user_message (str): ユーザーに表示するメッセージ
        status_code (int): HTTPステータスコード

    Returns:
        tuple: (JSONレスポンス, ステータスコード)

    Example:
        >>> return handle_error(e, "セッションの保存に失敗しました")
    """
    # エラーIDを生成（ログとの紐付け用）
    error_id = str(uuid.uuid4())[:8]

    # 詳細エラーログ（内部ログのみ、ユーザーには露出しない）
    logger.error(f"[ERROR-{error_id}] {type(e).__name__}: {str(e)}", exc_info=True)

    # ユーザーメッセージ（エラーIDを含める）
    return jsonify(create_response(
        'error',
        message=f"{user_message}（エラーID: {error_id}）"
    )), status_code


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


# ==================== リクエストフック ====================

@app.before_request
def ensure_server_session_id():
    """
    各リクエストの前にserver_session_idを確保

    リクエストごとにserver_session_idが存在することを保証し、
    存在しない場合は自動的に新しいIDを生成します。
    これにより、SessionStoreでのデータ管理が可能になります。
    """
    get_server_session_id()


# ==================== 基本ルート ====================

@app.route('/')
def index():
    """
    メイン画面を表示

    Returns:
        str: index.htmlのレンダリング結果
    """
    logger.info("メイン画面を表示")
    return render_template('index.html')


@app.route('/mapping')
def mapping():
    """
    マッピング管理画面を表示

    Returns:
        str: mapping.htmlのレンダリング結果
    """
    logger.info("マッピング管理画面を表示")
    return render_template('mapping.html')


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

    # セッションストアから処理結果を取得
    session_data = session_store.load(get_server_session_id()) or {}
    result_data = session_data.get('process_result')

    if result_data is None:
        logger.warning("処理結果がセッションに存在しません。メイン画面にリダイレクトします")
        return redirect(url_for('index'))

    return render_template('result.html', result=result_data)


# ==================== CSVアップロード機能 ====================

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

        # 7. セッションストアにファイルパスを保存
        try:
            session_data = session_store.load(get_server_session_id()) or {}
            session_data['uploaded_file_path'] = file_path
            session_data['uploaded_filename'] = filename
            session_store.save(get_server_session_id(), session_data)
        except Exception as e:
            # アップロードされたファイルを削除
            if os.path.exists(file_path):
                os.remove(file_path)
            return handle_error(e, "セッションの保存に失敗しました。再度お試しください")

        logger.info(f"ファイルアップロード成功: {safe_filename} ({file_size} bytes)")

        # 8. 古いファイルのクリーンアップ（非同期的に実行）
        cleanup_old_files(app.config['UPLOAD_FOLDER'])

        # 9. 古いセッションのクリーンアップ
        try:
            session_store.prune_expired()
        except Exception as e:
            logger.warning(f"セッションクリーンアップ中にエラー: {str(e)}")

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
        return handle_error(e, "ファイルのアップロードに失敗しました")


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
        # 1. セッションストアからファイルパス取得
        session_data = session_store.load(get_server_session_id()) or {}
        file_path = session_data.get('uploaded_file_path')

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

        # 4. セッションストアに全データを保存（後続のprocess処理用）
        try:
            session_data['csv_data'] = result['details']
            session_store.save(get_server_session_id(), session_data)
        except Exception as e:
            return handle_error(e, "セッションの保存に失敗しました。再度お試しください")

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
        return handle_error(e, "プレビュー取得に失敗しました")


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

        # 3. セッションストアからCSVデータ取得
        session_data = session_store.load(get_server_session_id()) or {}
        csv_data = session_data.get('csv_data')

        if not csv_data:
            logger.warning("CSVデータがセッションストアに存在しません")
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
                    'count': 0,
                    'by_category': {}  # カテゴリ別の詳細を追加
                }
            month_summary[month]['amount'] += amount
            month_summary[month]['count'] += 1

            # 月別・カテゴリ別サマリー
            if category not in month_summary[month]['by_category']:
                month_summary[month]['by_category'][category] = {
                    'amount': 0,
                    'count': 0,
                    'column': column
                }
            month_summary[month]['by_category'][category]['amount'] += amount
            month_summary[month]['by_category'][category]['count'] += 1

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

        # 11. セッションストアに処理結果を保存
        try:
            session_data['process_result'] = result_data
            session_store.save(get_server_session_id(), session_data)
        except Exception as e:
            return handle_error(e, "処理結果の保存に失敗しました。再度お試しください")

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
        return handle_error(e, "処理に失敗しました")


# ==================== マッピング管理API ====================

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

    except mapping_manager.MappingManagerError as e:
        logger.error(f"マッピング取得エラー: {e.message}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'マッピング一覧の取得に失敗しました: {e.message}'
        )), 500

    except Exception as e:
        return handle_error(e, "マッピング一覧の取得に失敗しました")


@app.route('/mapping/add', methods=['POST'])
def mapping_add():
    """
    新規マッピングを追加

    Request JSON:
        {
            'pattern': str,         # 店舗名パターン
            'category': str,        # カテゴリ名
            'column': str,          # 列記号（A-Z）
            'match_type': str       # マッチタイプ（exact, prefix, partial）
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
        required_fields = ['pattern', 'category', 'column', 'match_type']
        missing_fields = [f for f in required_fields if f not in request_data or not request_data[f]]

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
            message='同じ店舗名とマッチタイプの組み合わせが既に存在します'
        )), 400

    except mapping_manager.MappingManagerError as e:
        logger.error(f"マッピング追加エラー: {e.message}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'マッピングの追加に失敗しました: {e.message}'
        )), 500

    except Exception as e:
        return handle_error(e, "マッピングの追加に失敗しました")


@app.route('/mapping/edit/<int:mapping_id>', methods=['PUT'])
def mapping_edit(mapping_id: int):
    """
    既存マッピングを更新

    Args:
        mapping_id (int): マッピングID

    Request JSON:
        {
            'pattern': str (optional),
            'category': str (optional),
            'column': str (optional),
            'match_type': str (optional)
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
            f"store_name={updated_mapping['store_name']}"
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

    except mapping_manager.MappingManagerError as e:
        logger.error(f"マッピング更新エラー: {e.message}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'マッピングの更新に失敗しました: {e.message}'
        )), 500

    except Exception as e:
        return handle_error(e, "マッピングの更新に失敗しました")


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
        result = mapping_manager.delete_mapping(mapping_id)

        logger.info(f"マッピング削除成功: ID={mapping_id}")

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

    except mapping_manager.MappingManagerError as e:
        logger.error(f"マッピング削除エラー: {e.message}", exc_info=True)
        return jsonify(create_response(
            'error',
            message=f'マッピングの削除に失敗しました: {e.message}'
        )), 500

    except Exception as e:
        return handle_error(e, "マッピングの削除に失敗しました")


# ==================== エラーハンドリング・クリーンアップ ====================

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

    return jsonify(create_response(
        'error',
        message='指定されたリソースが見つかりません'
    )), 404


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

    return jsonify(create_response(
        'error',
        message='サーバー内部エラーが発生しました'
    )), 500


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


@app.route('/clear_session', methods=['POST'])
@csrf.exempt  # TODO: 全フロントエンド実装完了後にCSRF保護を有効化
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
        # セッションストアからファイルパス取得
        session_data = session_store.load(get_server_session_id()) or {}
        file_path = session_data.get('uploaded_file_path')

        # アップロードファイルの削除
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"アップロードファイルを削除: {file_path}")

        # セッションストアからデータ削除
        session_store.delete(get_server_session_id())

        # Cookieセッションもクリア
        session.clear()

        logger.info("セッションクリア完了")

        return jsonify(create_response(
            'success',
            message='セッションをクリアしました'
        ))

    except Exception as e:
        return handle_error(e, "セッションのクリアに失敗しました")


@app.route('/download/log', methods=['GET'])
def download_log():
    """
    処理ログをダウンロード

    Returns:
        file: ログファイル（text/plain）

    Raises:
        404: ログファイルが存在しない
        500: ファイル送信エラー
    """
    logger.info("ログダウンロード処理を開始")

    try:
        # ログファイルの存在確認
        log_file_path = app.config['LOG_FILE']

        if not os.path.exists(log_file_path):
            logger.warning(f"ログファイルが見つかりません: {log_file_path}")
            return jsonify(create_response(
                'error',
                message='ログファイルが存在しません'
            )), 404

        logger.info(f"ログファイル送信: {log_file_path}")

        # ファイル送信
        return send_file(
            log_file_path,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'app_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        )

    except Exception as e:
        return handle_error(e, "ログのダウンロードに失敗しました")


# ==================== セキュリティヘッダー設定 ====================

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
        response: Flaskレスポンスオブジェクト

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

    # MIMEスニッフィング防止
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # クリックジャッキング防止
    response.headers['X-Frame-Options'] = 'DENY'

    # リファラー制御
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # 不要な機能の無効化
    response.headers['Permissions-Policy'] = 'camera=(), geolocation=(), microphone=()'

    # HSTS（本番環境のみ、HTTPS必須）
    # FLASK_ENVがproductionの時のみ有効化（テスト/ステージング環境では無効）
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response


# ==================== アプリケーション起動 ====================

if __name__ == '__main__':
    logger.info("アプリケーションを起動します")
    logger.info(f"環境: {env}")
    logger.info(f"デバッグモード: {app.config['DEBUG']}")
    logger.info(f"アップロードフォルダ: {app.config['UPLOAD_FOLDER']}")

    # 古いセッションのクリーンアップ
    try:
        deleted_count = session_store.prune_expired()
        logger.info(f"古いセッションを削除: {deleted_count}件")
    except Exception as e:
        logger.warning(f"セッションクリーンアップ中にエラー: {str(e)}")

    app.run(
        host='127.0.0.1',  # ローカル限定設定（セキュリティ強化）
        port=5000,
        debug=app.config['DEBUG']
    )
