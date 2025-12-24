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

# ==================== アプリケーション初期化 ====================

# Flaskアプリケーション作成
app = Flask(__name__)

# 環境変数から環境名を取得（デフォルト: development）
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# アップロードフォルダの作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

# ==================== 定数定義 ====================

# デフォルトカテゴリと列（未登録店舗用）
DEFAULT_CATEGORY = '支払額'
DEFAULT_COLUMN = 'B'

# ==================== ヘルパー関数 ====================

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

    # セッションから処理結果を取得
    result_data = session.get('process_result')

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


# ==================== アプリケーション起動 ====================

if __name__ == '__main__':
    logger.info("アプリケーションを起動します")
    logger.info(f"環境: {env}")
    logger.info(f"デバッグモード: {app.config['DEBUG']}")
    logger.info(f"アップロードフォルダ: {app.config['UPLOAD_FOLDER']}")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )
