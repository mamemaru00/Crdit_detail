"""
ChatGPT分類モジュール

OpenAI APIを使用して未登録店舗を自動分類するモジュール。

主な機能:
- 未登録店舗のバッチ分類（最大10件/リクエスト）
- カテゴリマスタに準拠した分類（C～V列）
- 信頼度スコア付き分類結果
- エラーハンドリング（リトライ、タイムアウト、フォールバック）
- ログ記録（API呼び出し履歴、エラー内容）

使用例:
    >>> from modules.gpt_classifier import GPTClassifier
    >>> classifier = GPTClassifier(api_key='sk-...')
    >>> result = classifier.classify_stores(['ユシンヤ', 'AMAZON.CO.JP'])
    >>> result['ユシンヤ']
    {'category': '外食費', 'column': 'D', 'confidence': 'high', 'reasoning': '飲食店'}
"""

import json
import logging
import os
import time
import traceback
from datetime import datetime
from typing import List, Dict, Optional, Iterable
from openai import OpenAI, OpenAIError, APITimeoutError, RateLimitError

# config.pyのインポート
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


# ==================== ロガー設定 ====================

logger = logging.getLogger(__name__)

# GPT API専用ロガー設定
GPT_API_LOG = os.path.join('logs', 'gpt_api.log')
gpt_api_logger = logging.getLogger('gpt_api')
if not gpt_api_logger.handlers:
    os.makedirs(os.path.dirname(GPT_API_LOG), exist_ok=True)
    handler = logging.FileHandler(GPT_API_LOG, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(message)s'))
    gpt_api_logger.addHandler(handler)
    gpt_api_logger.propagate = False
gpt_api_logger.setLevel(logging.INFO)


# ==================== カテゴリマスタ定義 ====================

CATEGORY_MASTER = {
    'C': '食材費',
    'D': '外食費',
    'E': '自己投資費',
    'F': '書籍代',
    'G': '家電',
    'H': '雑貨費',
    'I': '衣服・化粧費',
    'J': '娯楽',
    'K': '旅行費',
    'O': '通信費',
    'R': '個人娯楽',
    'T': 'サブスク'
}

# カテゴリ名→列番号の逆引きマップ
CATEGORY_TO_COLUMN = {v: k for k, v in CATEGORY_MASTER.items()}

# デフォルトカテゴリ（分類不能時）
DEFAULT_CATEGORY = '雑貨費'
DEFAULT_COLUMN = 'H'


# ==================== カスタム例外クラス ====================

class GPTClassificationError(Exception):
    """GPT分類処理の基底例外クラス"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class GPTAPIError(GPTClassificationError):
    """OpenAI APIエラー"""
    pass


class GPTParseError(GPTClassificationError):
    """GPT応答のパースエラー"""
    pass


# ==================== GPT分類クラス ====================

class GPTClassifier:
    """
    ChatGPTを使用した店舗カテゴリ分類クラス

    Attributes:
        api_key (str): OpenAI APIキー
        model (str): 使用するGPTモデル（デフォルト: gpt-5）
        max_tokens (int): 最大トークン数（デフォルト: 2000）
        temperature (float): 温度パラメータ（デフォルト: 0.3）
        timeout (int): タイムアウト秒数（デフォルト: 30）
        max_retries (int): 最大リトライ回数（デフォルト: 3）
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: int = 30,
        max_retries: int = 3,
        batch_size: Optional[int] = None
    ):
        """
        GPT分類器を初期化する

        Args:
            api_key (str): OpenAI APIキー
            model (str): 使用するGPTモデル（デフォルト: gpt-5）
            max_tokens (int): 最大トークン数（デフォルト: 2000）
            temperature (float): 温度パラメータ（デフォルト: 0.3）
            timeout (int): タイムアウト秒数（デフォルト: 30）
            max_retries (int): 最大リトライ回数（デフォルト: 3）
            batch_size (Optional[int]): バッチサイズ（デフォルト: Config.GPT_BATCH_SIZE）

        Raises:
            ValueError: APIキーが空の場合
        """
        if not api_key:
            raise ValueError("OpenAI APIキーが設定されていません")

        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self.batch_size = batch_size or Config.GPT_BATCH_SIZE

        # OpenAIクライアント初期化
        self.client = OpenAI(api_key=api_key, timeout=timeout)

        logger.info(f"GPTClassifierを初期化しました: model={model}, max_tokens={max_tokens}, "
                   f"temperature={temperature}, timeout={timeout}s, max_retries={max_retries}, "
                   f"batch_size={self.batch_size}")

    def classify_stores(self, store_names: List[str]) -> Dict[str, Dict[str, str]]:
        """
        未登録店舗をバッチ分類する（複数バッチ対応）

        Args:
            store_names (List[str]): 分類対象の店舗名リスト

        Returns:
            Dict[str, Dict[str, str]]: 店舗名をキーとした分類結果
                {
                    "store_name": {
                        "category": "外食費",
                        "column": "D",
                        "confidence": "high",  # high/medium/low
                        "reasoning": "飲食店チェーン名のため"
                    }
                }

        Raises:
            GPTAPIError: API呼び出しエラー時
            GPTParseError: 応答パースエラー時

        Example:
            >>> classifier = GPTClassifier(api_key='sk-...')
            >>> result = classifier.classify_stores(['ユシンヤ', 'AMAZON.CO.JP'])
            >>> result['ユシンヤ']['category']
            '外食費'
        """
        # 店舗名の正規化（重複排除、空文字除去）
        normalized = self._prepare_store_names(store_names)
        if not normalized:
            logger.warning("分類対象の店舗名が空または無効です")
            return {}

        logger.info(f"ChatGPT分類を開始します: {len(normalized)}件（元: {len(store_names)}件）")

        # 複数バッチに分割して処理
        results: Dict[str, Dict[str, str]] = {}
        for batch_index, batch in enumerate(self._chunked(normalized, self.batch_size), start=1):
            logger.info(f"ChatGPT分類バッチ開始: #{batch_index} ({len(batch)}件)")
            batch_result = self._classify_batch(batch_index, batch)
            results.update(batch_result)

        logger.info(f"ChatGPT分類が完了しました: {len(results)}件分類")
        return results

    def _prepare_store_names(self, store_names: Iterable[str]) -> List[str]:
        """
        店舗名リストを正規化する（重複排除、空文字除去）

        Args:
            store_names (Iterable[str]): 元の店舗名リスト

        Returns:
            List[str]: 正規化後の店舗名リスト
        """
        seen = set()
        normalized = []
        for name in store_names or []:
            if not name:
                continue
            key = name.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            normalized.append(key)
        return normalized

    def _chunked(self, items: List[str], batch_size: int) -> Iterable[List[str]]:
        """
        リストを指定サイズのチャンクに分割する

        Args:
            items (List[str]): 分割対象のリスト
            batch_size (int): チャンクサイズ

        Yields:
            List[str]: チャンク
        """
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]

    def _classify_batch(self, batch_index: int, batch: List[str]) -> Dict[str, Dict[str, str]]:
        """
        1バッチ分の店舗を分類する（リトライ処理付き）

        Args:
            batch_index (int): バッチ番号（1から始まる）
            batch (List[str]): 分類対象の店舗名リスト

        Returns:
            Dict[str, Dict[str, str]]: 分類結果
        """
        # プロンプト生成
        prompt = self._build_prompt(batch)
        last_error: Optional[Exception] = None

        # リトライループ
        for attempt in range(1, self.max_retries + 1):
            started = time.perf_counter()
            try:
                logger.debug(f"API呼び出し試行 {attempt}/{self.max_retries} (batch #{batch_index})")

                # OpenAI API呼び出し
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "あなたは店舗名から商品カテゴリを分類するエキスパートです。日本の店舗・サービスに精通しています。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    response_format={"type": "json_object"}
                )

                # 応答テキスト取得
                response_text = response.choices[0].message.content
                logger.debug(f"API応答を受信しました（{len(response_text)}文字）")

                # 応答パース
                parsed = self._parse_response(response_text)

                # 部分的成功の処理（API応答に含まれない店舗にデフォルトを設定）
                merged = self._merge_partial_results(batch, parsed)

                # 成功メトリクスのログ記録
                self._log_api_metrics(batch_index, attempt, batch, True, started)

                logger.info(f"ChatGPT分類成功: batch #{batch_index} ({len(merged)}件)")
                return merged

            except RateLimitError as e:
                # レート制限エラー（429 Too Many Requests）
                last_error = e
                self._log_api_metrics(batch_index, attempt, batch, False, started, e)
                logger.warning(
                    f"レート制限エラー（429）が発生しました（試行 {attempt}/{self.max_retries}, batch #{batch_index}）: {str(e)}"
                    f"\n  → 対処法: GPT_BATCH_SIZE を減らす（現在: {self.batch_size}）、または時間を空けて再実行してください"
                )
                self._sleep_with_backoff(attempt, rate_limited=True)

            except APITimeoutError as e:
                # タイムアウトエラー
                last_error = e
                self._log_api_metrics(batch_index, attempt, batch, False, started, e)
                logger.warning(f"タイムアウトエラーが発生しました（試行 {attempt}/{self.max_retries}, batch #{batch_index}）: {str(e)}")
                self._sleep_with_backoff(attempt)

            except OpenAIError as e:
                # その他のOpenAIエラー
                last_error = e
                self._log_api_metrics(batch_index, attempt, batch, False, started, e)
                logger.error(f"OpenAI APIエラーが発生しました（試行 {attempt}/{self.max_retries}, batch #{batch_index}）: {str(e)}")
                self._sleep_with_backoff(attempt)

            except Exception as e:
                # 予期しないエラー
                last_error = e
                self._log_api_metrics(batch_index, attempt, batch, False, started, e, traceback.format_exc())
                logger.error(f"予期しないエラーが発生しました (batch #{batch_index}): {str(e)}")
                break

        # 最大リトライ回数に達した場合、このバッチのみデフォルトカテゴリを返却
        logger.error(f"最大リトライ回数に達しました (batch #{batch_index})。このバッチはデフォルトカテゴリを返却します")
        return self._handle_error(last_error or Exception("不明なエラー"), batch)

    def _sleep_with_backoff(self, attempt: int, rate_limited: bool = False) -> None:
        """
        指数バックオフでスリープする

        Args:
            attempt (int): 試行回数
            rate_limited (bool): Rate Limit（429）エラーの場合True（より長い待機時間を適用）
        """
        if attempt < self.max_retries:
            if rate_limited:
                # Rate Limit時は長めの待機（10s → 30s → 60s）
                wait_time = min(10 * (3 ** (attempt - 1)), 60)
            else:
                wait_time = 2 ** attempt
            logger.info(f"{wait_time}秒待機してリトライします")
            time.sleep(wait_time)

    def _merge_partial_results(
        self, expected: List[str], parsed: Dict[str, Dict[str, str]]
    ) -> Dict[str, Dict[str, str]]:
        """
        API応答とバッチ入力をマージする（部分的成功の処理）

        Args:
            expected (List[str]): バッチ入力の店舗名リスト
            parsed (Dict[str, Dict[str, str]]): API応答のパース結果

        Returns:
            Dict[str, Dict[str, str]]: マージ済み分類結果
        """
        merged: Dict[str, Dict[str, str]] = {}
        for store in expected:
            if store in parsed:
                merged[store] = parsed[store]
            else:
                logger.warning(f"API応答に店舗 '{store}' が含まれませんでした。デフォルトを設定します")
                merged[store] = {
                    'category': DEFAULT_CATEGORY,
                    'column': DEFAULT_COLUMN,
                    'confidence': 'low',
                    'reasoning': 'API応答に結果が含まれなかったためデフォルト'
                }
        return merged

    def _log_api_metrics(
        self,
        batch_index: int,
        attempt: int,
        batch: List[str],
        success: bool,
        started: float,
        error: Optional[Exception] = None,
        stacktrace: Optional[str] = None,
    ) -> None:
        """
        API呼び出しメトリクスをログに記録する

        Args:
            batch_index (int): バッチ番号
            attempt (int): 試行回数
            batch (List[str]): バッチ店舗名リスト
            success (bool): 成功/失敗
            started (float): 開始時刻（time.perf_counter）
            error (Optional[Exception]): エラーオブジェクト
            stacktrace (Optional[str]): スタックトレース
        """
        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "batch_index": batch_index,
            "attempt": attempt,
            "store_count": len(batch),
            "success": success,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
        if error:
            payload["error"] = str(error)
            payload["error_type"] = type(error).__name__
            if stacktrace:
                payload["stacktrace"] = stacktrace
        gpt_api_logger.info(json.dumps(payload, ensure_ascii=False))

    def _build_prompt(self, store_names: List[str]) -> str:
        """
        ChatGPTプロンプトを生成する

        Args:
            store_names (List[str]): 分類対象の店舗名リスト

        Returns:
            str: 生成されたプロンプト
        """
        # カテゴリマスタをJSON形式で整形
        category_list = [
            f"  - {column}列: {category}"
            for column, category in CATEGORY_MASTER.items()
        ]
        category_text = "\n".join(category_list)

        # 店舗名リストを整形
        store_list = "\n".join([f"  - {name}" for name in store_names])

        # Few-shot例
        examples = """
例1:
店舗名: ユシンヤ
分類結果:
{
  "category": "外食費",
  "column": "D",
  "confidence": "high",
  "reasoning": "飲食店チェーン名のため外食費に分類"
}

例2:
店舗名: AMAZON.CO.JP
分類結果:
{
  "category": "雑貨費",
  "column": "H",
  "confidence": "medium",
  "reasoning": "オンラインショップは購入品により変動するため、デフォルトの雑貨費に分類"
}

例3:
店舗名: セブンイレブン
分類結果:
{
  "category": "食材費",
  "column": "C",
  "confidence": "high",
  "reasoning": "コンビニエンスストアは主に食品・飲料を購入する頻度が高いため食材費に分類"
}

例4:
店舗名: ユニクロ
分類結果:
{
  "category": "衣服・化粧費",
  "column": "I",
  "confidence": "high",
  "reasoning": "アパレルチェーンのため衣服・化粧費に分類"
}

例5:
店舗名: Netflix
分類結果:
{
  "category": "サブスク",
  "column": "T",
  "confidence": "high",
  "reasoning": "定額制動画配信サービスのためサブスクに分類"
}
"""

        # プロンプト構築
        prompt = f"""
以下の店舗名を、家計簿のカテゴリに分類してください。

# カテゴリマスタ（利用可能なカテゴリ）
{category_text}

# 分類ルール
1. 店舗名の特徴（業種、商品、サービス）から最適なカテゴリを判定する
2. 複数候補がある場合は、最も高頻度の利用パターンを選択する
3. オンラインショップなど購入品が特定できない場合は「雑貨費（H列）」をデフォルトとする
4. confidence（信頼度）は以下の基準で判定する:
   - high: 店舗名から明確にカテゴリが特定できる（専門店、チェーン店など）
   - medium: カテゴリは推定できるが、複数の可能性がある（総合店、オンラインショップなど）
   - low: カテゴリの特定が困難（不明な店舗名、曖昧な名称など）

# 分類例
{examples}

# 分類対象の店舗名（{len(store_names)}件）
{store_list}

# 出力形式
JSON形式で以下の構造で全店舗の分類結果を出力してください:
{{
  "店舗名1": {{
    "category": "カテゴリ名",
    "column": "列番号",
    "confidence": "high|medium|low",
    "reasoning": "分類理由（50文字以内）"
  }},
  "店舗名2": {{ ... }},
  ...
}}

注意:
- 必ずJSON形式で出力してください
- すべての店舗名に対して分類結果を返してください
- カテゴリ名と列番号はカテゴリマスタに存在するもののみを使用してください
"""

        return prompt.strip()

    def _parse_response(self, response: str) -> Dict[str, Dict[str, str]]:
        """
        GPT応答のJSON解析

        Args:
            response (str): GPTからの応答テキスト（JSON形式）

        Returns:
            Dict[str, Dict[str, str]]: パースされた分類結果

        Raises:
            GPTParseError: JSON解析エラー時
        """
        try:
            # JSON解析
            data = json.loads(response)

            if not isinstance(data, dict):
                raise GPTParseError(
                    f"応答がdict型ではありません: {type(data)}",
                    details={'response': response[:200]}
                )

            # バリデーション
            result = {}
            for store_name, classification in data.items():
                if not isinstance(classification, dict):
                    logger.warning(f"店舗 '{store_name}' の分類結果が不正です（スキップ）: {classification}")
                    continue

                # 必須フィールドチェック
                category = classification.get('category')
                column = classification.get('column')
                confidence = classification.get('confidence', 'low')
                reasoning = classification.get('reasoning', '自動分類')

                if not category or not column:
                    logger.warning(f"店舗 '{store_name}' の必須フィールドが不足しています（デフォルトカテゴリ設定）")
                    result[store_name] = {
                        'category': DEFAULT_CATEGORY,
                        'column': DEFAULT_COLUMN,
                        'confidence': 'low',
                        'reasoning': '分類不能（デフォルト）'
                    }
                    continue

                # カテゴリマスタと照合
                if column not in CATEGORY_MASTER:
                    logger.warning(f"店舗 '{store_name}' の列番号が不正です（{column}）。デフォルトカテゴリ設定")
                    result[store_name] = {
                        'category': DEFAULT_CATEGORY,
                        'column': DEFAULT_COLUMN,
                        'confidence': 'low',
                        'reasoning': '列番号不正（デフォルト）'
                    }
                    continue

                # カテゴリ名と列番号の整合性チェック
                expected_category = CATEGORY_MASTER[column]
                if category != expected_category:
                    logger.warning(f"店舗 '{store_name}' のカテゴリ名と列番号が不整合です "
                                 f"（category={category}, column={column}, expected={expected_category}）。"
                                 f"列番号を優先します")
                    category = expected_category

                result[store_name] = {
                    'category': category,
                    'column': column,
                    'confidence': confidence,
                    'reasoning': reasoning
                }

            logger.debug(f"応答パース成功: {len(result)}件の分類結果を取得")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {str(e)}")
            logger.debug(f"応答テキスト: {response[:500]}")
            raise GPTParseError(
                f"応答のJSON解析に失敗しました: {str(e)}",
                details={'response': response[:200], 'error': str(e)}
            )
        except Exception as e:
            logger.error(f"応答パース中にエラーが発生しました: {str(e)}")
            raise GPTParseError(
                f"応答のパース中にエラーが発生しました: {str(e)}",
                details={'error': str(e)}
            )

    def _handle_error(self, error: Exception, store_names: List[str] = None) -> Dict[str, Dict[str, str]]:
        """
        エラーハンドリング（デフォルトカテゴリ返却）

        Args:
            error (Exception): 発生したエラー
            store_names (List[str]): 分類対象の店舗名リスト（オプション）

        Returns:
            Dict[str, Dict[str, str]]: デフォルトカテゴリを設定した分類結果
        """
        logger.error(f"GPT分類エラー: {str(error)}")
        logger.info(f"全店舗にデフォルトカテゴリ（{DEFAULT_CATEGORY} / {DEFAULT_COLUMN}列）を設定します")

        # Rate Limitエラーの場合、ユーザー向けガイダンスをログ出力
        if isinstance(error, RateLimitError):
            logger.warning(
                "Rate Limit（429）エラーによりデフォルトカテゴリにフォールバックしました。"
                "\n  → 対処法: (1) 時間を空けて再実行 (2) GPT_BATCH_SIZE を減らす (3) OpenAI課金プランを確認"
            )

        result = {}
        if store_names:
            # エラー種別に応じたユーザー向けメッセージ
            if isinstance(error, RateLimitError):
                error_msg = 'API制限超過（デフォルト）: 時間を空けて再実行してください'
            else:
                error_msg = f'分類エラー（デフォルト）: {str(error)[:50]}'

            for store_name in store_names:
                result[store_name] = {
                    'category': DEFAULT_CATEGORY,
                    'column': DEFAULT_COLUMN,
                    'confidence': 'low',
                    'reasoning': error_msg
                }

        return result
