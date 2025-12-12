#!/bin/bash
#
# カバレッジ計測スクリプト
#
# 使用方法:
#   chmod +x run_coverage.sh
#   ./run_coverage.sh
#
# このスクリプトはpytestを使用してmodules/category_logic.pyのテストカバレッジを計測します。
# HTMLレポートとターミナル出力の両方を生成します。

set -e

echo "======================================"
echo "  カバレッジ計測開始"
echo "======================================"

# プロジェクトルートに移動
cd "$(dirname "$0")"

# Pythonとpytestのバージョン確認
echo ""
echo "[確認] Pythonバージョン:"
python --version

echo ""
echo "[確認] pytestバージョン:"
pytest --version

# テスト実行 & カバレッジ計測
echo ""
echo "[実行] pytest + カバレッジ計測..."
pytest tests/ \
  --cov=modules.category_logic \
  --cov-report=html \
  --cov-report=term-missing \
  --cov-report=term:skip-covered \
  -v

# カバレッジレポートの場所を表示
echo ""
echo "======================================"
echo "  カバレッジ計測完了"
echo "======================================"
echo ""
echo "HTMLレポート: htmlcov/index.html"
echo ""
echo "ブラウザで開くには:"
echo "  open htmlcov/index.html"
echo ""
