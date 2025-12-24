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
