"""
Phase 7.2: ChatGPT分類モジュール（modules/gpt_classifier.py）の単体テスト

このモジュールは以下のテストケースを実行します:

正常系（10ケース）:
1. GPTClassifierの正常初期化（APIキー有効）
2. カスタムbatch_sizeでの初期化
3. 単一バッチ（≤50件）の正常分類
4. 複数バッチ（60件）の分類
5. 店舗名の重複排除
6. 空文字・Noneの除去
7. チャンク分割の検証
8. 部分的成功の処理（全店舗がAPI応答に含まれる）
9. 部分的成功の処理（一部店舗がAPI応答に欠損）
10. 正常なJSON応答のパース

異常系（8ケース）:
1. APIキー空でValueError
2. 空リストで空dictを返却
3. RateLimitError後リトライ成功
4. APITimeoutError後リトライ成功
5. 最大リトライ回数超過でデフォルト返却
6. 不正JSONでGPTParseError
7. 必須フィールド欠損でデフォルト設定
8. 不正な列番号でデフォルト設定

エラーハンドリング（4ケース）:
1. エラー時に全店舗デフォルト化
2. 成功時のログ記録
3. エラー時のログ記録（stacktrace含む）
4. OpenAIError発生時のフォールバック
"""

import pytest
import json
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List

from modules.gpt_classifier import (
    GPTClassifier,
    GPTClassificationError,
    GPTAPIError,
    GPTParseError,
    CATEGORY_MASTER,
    DEFAULT_CATEGORY,
    DEFAULT_COLUMN
)
from openai import OpenAIError, APITimeoutError, RateLimitError
import httpx


def _make_rate_limit_error(message="Rate limit exceeded"):
    """openai>=1.0.0対応: RateLimitErrorにはresponseとbodyが必須"""
    mock_response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )
    return RateLimitError(message, response=mock_response, body=None)


# ==================== フィクスチャ ====================

@pytest.fixture
def valid_api_key():
    """有効なAPIキー"""
    return "sk-test-valid-api-key-12345"


@pytest.fixture
def mock_openai_client():
    """OpenAIクライアントのモック"""
    with patch('modules.gpt_classifier.OpenAI') as mock:
        yield mock


@pytest.fixture
def sample_stores():
    """サンプル店舗名リスト（10件）"""
    return [
        'ユシンヤ',
        'AMAZON.CO.JP',
        'セブンイレブン',
        'ユニクロ',
        'Netflix',
        'スターバックス',
        'マクドナルド',
        'ビックカメラ',
        '紀伊國屋書店',
        'ローソン'
    ]


@pytest.fixture
def sample_classification_result():
    """サンプル分類結果"""
    return {
        'ユシンヤ': {
            'category': '外食費',
            'column': 'D',
            'confidence': 'high',
            'reasoning': '飲食店チェーン名のため'
        },
        'AMAZON.CO.JP': {
            'category': '雑貨費',
            'column': 'H',
            'confidence': 'medium',
            'reasoning': 'オンラインショップのため'
        }
    }


@pytest.fixture
def mock_gpt_response(sample_classification_result):
    """モックGPT応答"""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps(sample_classification_result, ensure_ascii=False)
    return mock_response


# ==================== 正常系テスト ====================

def test_init_success(valid_api_key, mock_openai_client):
    """Test 1: GPTClassifierの正常初期化"""
    classifier = GPTClassifier(api_key=valid_api_key)

    assert classifier.api_key == valid_api_key
    assert classifier.model == "gpt-5"
    assert classifier.max_tokens == 2000
    assert classifier.temperature == 0.3
    assert classifier.timeout == 30
    assert classifier.max_retries == 3
    assert classifier.batch_size == 50  # Config.GPT_BATCH_SIZE


def test_init_with_custom_batch_size(valid_api_key, mock_openai_client):
    """Test 2: カスタムbatch_sizeでの初期化"""
    classifier = GPTClassifier(api_key=valid_api_key, batch_size=25)

    assert classifier.batch_size == 25


def test_classify_single_batch(valid_api_key, mock_openai_client, sample_stores, mock_gpt_response):
    """Test 3: 単一バッチ（≤50件）の正常分類"""
    # OpenAI APIのモック設定
    mock_client_instance = mock_openai_client.return_value
    mock_client_instance.chat.completions.create.return_value = mock_gpt_response

    classifier = GPTClassifier(api_key=valid_api_key)

    # 2件のみでテスト（mock_gpt_responseが2件を返す）
    result = classifier.classify_stores(sample_stores[:2])

    assert len(result) == 2
    assert 'ユシンヤ' in result
    assert result['ユシンヤ']['category'] == '外食費'
    assert result['ユシンヤ']['column'] == 'D'


def test_classify_multiple_batches(valid_api_key, mock_openai_client):
    """Test 4: 複数バッチ（60件）の分類"""
    # 60件の店舗名リスト（batch_size=50で2バッチ）
    stores = [f'店舗{i}' for i in range(60)]

    # モック設定（各バッチで異なる応答を返す）
    mock_client_instance = mock_openai_client.return_value

    def create_mock_response(store_batch):
        result = {store: {
            'category': '雑貨費',
            'column': 'H',
            'confidence': 'low',
            'reasoning': 'テスト'
        } for store in store_batch}
        mock_resp = Mock()
        mock_resp.choices = [Mock()]
        mock_resp.choices[0].message.content = json.dumps(result, ensure_ascii=False)
        return mock_resp

    # _classify_batchメソッドをモック
    with patch.object(GPTClassifier, '_classify_batch') as mock_classify_batch:
        # 各バッチで対応する結果を返す
        mock_classify_batch.side_effect = [
            {f'店舗{i}': {'category': '雑貨費', 'column': 'H', 'confidence': 'low', 'reasoning': 'バッチ1'} for i in range(50)},
            {f'店舗{i}': {'category': '雑貨費', 'column': 'H', 'confidence': 'low', 'reasoning': 'バッチ2'} for i in range(50, 60)}
        ]

        classifier = GPTClassifier(api_key=valid_api_key, batch_size=50)
        result = classifier.classify_stores(stores)

        # 60件全て分類されたことを確認
        assert len(result) == 60
        assert '店舗0' in result
        assert '店舗59' in result

        # 2回のバッチ処理が実行されたことを確認
        assert mock_classify_batch.call_count == 2


def test_prepare_store_names_deduplication(valid_api_key, mock_openai_client):
    """Test 5: 店舗名の重複排除"""
    classifier = GPTClassifier(api_key=valid_api_key)

    stores_with_duplicates = ['A', 'B', 'A', 'C', 'B', 'D']
    normalized = classifier._prepare_store_names(stores_with_duplicates)

    assert len(normalized) == 4
    assert normalized == ['A', 'B', 'C', 'D']


def test_prepare_store_names_empty_removal(valid_api_key, mock_openai_client):
    """Test 6: 空文字・Noneの除去"""
    classifier = GPTClassifier(api_key=valid_api_key)

    stores_with_empty = ['A', '', None, '  ', 'B', '', 'C']
    normalized = classifier._prepare_store_names(stores_with_empty)

    assert len(normalized) == 3
    assert normalized == ['A', 'B', 'C']


def test_chunked(valid_api_key, mock_openai_client):
    """Test 7: チャンク分割の検証"""
    classifier = GPTClassifier(api_key=valid_api_key)

    items = list(range(25))
    chunks = list(classifier._chunked(items, 10))

    assert len(chunks) == 3
    assert chunks[0] == list(range(10))
    assert chunks[1] == list(range(10, 20))
    assert chunks[2] == list(range(20, 25))


def test_merge_partial_results_complete(valid_api_key, mock_openai_client):
    """Test 8: 部分的成功の処理（全店舗がAPI応答に含まれる）"""
    classifier = GPTClassifier(api_key=valid_api_key)

    expected = ['店舗A', '店舗B', '店舗C']
    parsed = {
        '店舗A': {'category': '外食費', 'column': 'D', 'confidence': 'high', 'reasoning': 'テスト'},
        '店舗B': {'category': '雑貨費', 'column': 'H', 'confidence': 'medium', 'reasoning': 'テスト'},
        '店舗C': {'category': '食材費', 'column': 'C', 'confidence': 'high', 'reasoning': 'テスト'}
    }

    merged = classifier._merge_partial_results(expected, parsed)

    assert len(merged) == 3
    assert merged['店舗A']['category'] == '外食費'
    assert merged['店舗B']['category'] == '雑貨費'
    assert merged['店舗C']['category'] == '食材費'


def test_merge_partial_results_partial(valid_api_key, mock_openai_client):
    """Test 9: 部分的成功の処理（一部店舗がAPI応答に欠損）"""
    classifier = GPTClassifier(api_key=valid_api_key)

    expected = ['店舗A', '店舗B', '店舗C']
    parsed = {
        '店舗A': {'category': '外食費', 'column': 'D', 'confidence': 'high', 'reasoning': 'テスト'}
        # 店舗B, 店舗Cは欠損
    }

    merged = classifier._merge_partial_results(expected, parsed)

    assert len(merged) == 3
    assert merged['店舗A']['category'] == '外食費'
    # 欠損した店舗はデフォルトカテゴリ
    assert merged['店舗B']['category'] == DEFAULT_CATEGORY
    assert merged['店舗B']['column'] == DEFAULT_COLUMN
    assert merged['店舗B']['confidence'] == 'low'
    assert merged['店舗C']['category'] == DEFAULT_CATEGORY


def test_parse_response_valid_json(valid_api_key, mock_openai_client):
    """Test 10: 正常なJSON応答のパース"""
    classifier = GPTClassifier(api_key=valid_api_key)

    valid_response = json.dumps({
        '店舗A': {
            'category': '外食費',
            'column': 'D',
            'confidence': 'high',
            'reasoning': 'テスト'
        }
    }, ensure_ascii=False)

    parsed = classifier._parse_response(valid_response)

    assert len(parsed) == 1
    assert '店舗A' in parsed
    assert parsed['店舗A']['category'] == '外食費'


# ==================== 異常系テスト ====================

def test_init_empty_api_key(mock_openai_client):
    """Test 11: APIキー空でValueError"""
    with pytest.raises(ValueError, match="OpenAI APIキーが設定されていません"):
        GPTClassifier(api_key="")


def test_classify_empty_list(valid_api_key, mock_openai_client):
    """Test 12: 空リストで空dictを返却"""
    classifier = GPTClassifier(api_key=valid_api_key)

    result = classifier.classify_stores([])

    assert result == {}


def test_classify_rate_limit_retry_success(valid_api_key, mock_openai_client):
    """Test 13: RateLimitError後リトライ成功"""
    mock_client_instance = mock_openai_client.return_value

    # 1回目: RateLimitError、2回目: 成功
    success_response = Mock()
    success_response.choices = [Mock()]
    success_response.choices[0].message.content = json.dumps({
        '店舗A': {'category': '外食費', 'column': 'D', 'confidence': 'high', 'reasoning': 'テスト'}
    }, ensure_ascii=False)

    mock_client_instance.chat.completions.create.side_effect = [
        _make_rate_limit_error("Rate limit exceeded"),
        success_response
    ]

    # time.sleepをモック化（テスト高速化）
    with patch('time.sleep'):
        classifier = GPTClassifier(api_key=valid_api_key)
        result = classifier.classify_stores(['店舗A'])

        assert len(result) == 1
        assert '店舗A' in result
        assert result['店舗A']['category'] == '外食費'


def test_classify_timeout_retry_success(valid_api_key, mock_openai_client):
    """Test 14: APITimeoutError後リトライ成功"""
    mock_client_instance = mock_openai_client.return_value

    # 1回目: Timeout、2回目: 成功
    success_response = Mock()
    success_response.choices = [Mock()]
    success_response.choices[0].message.content = json.dumps({
        '店舗A': {'category': '外食費', 'column': 'D', 'confidence': 'high', 'reasoning': 'テスト'}
    }, ensure_ascii=False)

    mock_client_instance.chat.completions.create.side_effect = [
        APITimeoutError("Request timeout"),
        success_response
    ]

    with patch('time.sleep'):
        classifier = GPTClassifier(api_key=valid_api_key)
        result = classifier.classify_stores(['店舗A'])

        assert len(result) == 1
        assert result['店舗A']['category'] == '外食費'


def test_classify_max_retries_exceeded(valid_api_key, mock_openai_client):
    """Test 15: 最大リトライ回数超過でデフォルト返却"""
    mock_client_instance = mock_openai_client.return_value

    # 全てRateLimitError
    mock_client_instance.chat.completions.create.side_effect = _make_rate_limit_error("Rate limit exceeded")

    with patch('time.sleep'):
        classifier = GPTClassifier(api_key=valid_api_key, max_retries=3)
        result = classifier.classify_stores(['店舗A', '店舗B'])

        # デフォルトカテゴリが設定される
        assert len(result) == 2
        assert result['店舗A']['category'] == DEFAULT_CATEGORY
        assert result['店舗A']['column'] == DEFAULT_COLUMN
        assert result['店舗A']['confidence'] == 'low'


def test_parse_response_invalid_json(valid_api_key, mock_openai_client):
    """Test 16: 不正JSONでGPTParseError"""
    classifier = GPTClassifier(api_key=valid_api_key)

    invalid_json = "This is not JSON"

    with pytest.raises(GPTParseError):
        classifier._parse_response(invalid_json)


def test_parse_response_missing_fields(valid_api_key, mock_openai_client):
    """Test 17: 必須フィールド欠損でデフォルト設定"""
    classifier = GPTClassifier(api_key=valid_api_key)

    # categoryフィールド欠損
    response_with_missing_field = json.dumps({
        '店舗A': {
            'column': 'D',
            'confidence': 'high',
            'reasoning': 'テスト'
        }
    }, ensure_ascii=False)

    parsed = classifier._parse_response(response_with_missing_field)

    # デフォルトカテゴリが設定される
    assert parsed['店舗A']['category'] == DEFAULT_CATEGORY
    assert parsed['店舗A']['column'] == DEFAULT_COLUMN


def test_parse_response_invalid_column(valid_api_key, mock_openai_client):
    """Test 18: 不正な列番号でデフォルト設定"""
    classifier = GPTClassifier(api_key=valid_api_key)

    # 不正な列番号（ZはCATEGORY_MASTERに存在しない）
    response_with_invalid_column = json.dumps({
        '店舗A': {
            'category': '外食費',
            'column': 'Z',
            'confidence': 'high',
            'reasoning': 'テスト'
        }
    }, ensure_ascii=False)

    parsed = classifier._parse_response(response_with_invalid_column)

    # デフォルトカテゴリが設定される
    assert parsed['店舗A']['category'] == DEFAULT_CATEGORY
    assert parsed['店舗A']['column'] == DEFAULT_COLUMN


# ==================== エラーハンドリングテスト ====================

def test_handle_error_with_store_names(valid_api_key, mock_openai_client):
    """Test 19: エラー時に全店舗デフォルト化"""
    classifier = GPTClassifier(api_key=valid_api_key)

    error = Exception("Test error")
    stores = ['店舗A', '店舗B', '店舗C']

    result = classifier._handle_error(error, stores)

    assert len(result) == 3
    for store in stores:
        assert result[store]['category'] == DEFAULT_CATEGORY
        assert result[store]['column'] == DEFAULT_COLUMN
        assert result[store]['confidence'] == 'low'
        assert 'Test error' in result[store]['reasoning']


def test_log_api_metrics_success(valid_api_key, mock_openai_client, tmp_path):
    """Test 20: 成功時のログ記録"""
    # 一時ログファイル作成
    log_file = tmp_path / "gpt_api.log"

    with patch('modules.gpt_classifier.GPT_API_LOG', str(log_file)):
        with patch('modules.gpt_classifier.gpt_api_logger') as mock_logger:
            classifier = GPTClassifier(api_key=valid_api_key)

            started = time.perf_counter()
            time.sleep(0.01)  # 少し待機

            classifier._log_api_metrics(
                batch_index=1,
                attempt=1,
                batch=['店舗A', '店舗B'],
                success=True,
                started=started
            )

            # ログが呼び出されたことを確認
            assert mock_logger.info.called

            # ログ内容の確認
            call_args = mock_logger.info.call_args[0][0]
            log_data = json.loads(call_args)

            assert log_data['batch_index'] == 1
            assert log_data['attempt'] == 1
            assert log_data['store_count'] == 2
            assert log_data['success'] is True
            assert log_data['duration_ms'] >= 10  # 最低10ms


def test_log_api_metrics_error(valid_api_key, mock_openai_client):
    """Test 21: エラー時のログ記録（stacktrace含む）"""
    with patch('modules.gpt_classifier.gpt_api_logger') as mock_logger:
        classifier = GPTClassifier(api_key=valid_api_key)

        started = time.perf_counter()
        error = _make_rate_limit_error("Rate limit exceeded")
        stacktrace = "Traceback (most recent call last):\n  ..."

        classifier._log_api_metrics(
            batch_index=1,
            attempt=1,
            batch=['店舗A'],
            success=False,
            started=started,
            error=error,
            stacktrace=stacktrace
        )

        # ログが呼び出されたことを確認
        assert mock_logger.info.called

        # ログ内容の確認
        call_args = mock_logger.info.call_args[0][0]
        log_data = json.loads(call_args)

        assert log_data['success'] is False
        assert log_data['error'] == "Rate limit exceeded"
        assert log_data['error_type'] == "RateLimitError"
        assert log_data['stacktrace'] == stacktrace


def test_openai_error_fallback(valid_api_key, mock_openai_client):
    """Test 22: OpenAIError発生時のフォールバック"""
    mock_client_instance = mock_openai_client.return_value

    # OpenAIError発生
    mock_client_instance.chat.completions.create.side_effect = OpenAIError("API Error")

    with patch('time.sleep'):
        classifier = GPTClassifier(api_key=valid_api_key, max_retries=2)
        result = classifier.classify_stores(['店舗A'])

        # デフォルトカテゴリが設定される
        assert len(result) == 1
        assert result['店舗A']['category'] == DEFAULT_CATEGORY
        assert result['店舗A']['confidence'] == 'low'
