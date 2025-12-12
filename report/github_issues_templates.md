# Step 2.2 改善項目 - GitHub Issues テンプレート

以下のIssueをGitHub Web UIで作成してください。

---

## Issue 1: 【中優先度】modules/category_logic.pyの使用例ドキュメント追加

**Title**: 【中優先度】modules/category_logic.pyの使用例ドキュメント追加

**Labels**: enhancement, documentation, priority:medium

**Body**:
```
## 概要
modules/category_logic.pyのモジュールdocstringに実践的な使用例を追加する。

## 目的
新規開発者のオンボーディング向上

## 実装内容
モジュールdocstringに以下の使用例を追加:

```python
使用例:
    from modules.category_logic import load_mapping_data, determine_category

    # マッピングデータ読み込み
    mapping_data = load_mapping_data('config/mapping.json')

    # カテゴリ判定
    result = determine_category('ユシンヤ', mapping_data)
    print(result['category'])  # '外食費'
    print(result['column'])    # 'C'
```

## 工数目安
1-2時間

## 優先度
中

## 参照ドキュメント
- report/phase6_integration_verification_report.md（8.3.1節）
- report/step_2_2_completion_report.md（9.2.2節）

## 関連ファイル
- modules/category_logic.py
```

---

## Issue 2: 【中優先度】未カバー行の理由説明コメント追加

**Title**: 【中優先度】未カバー行の理由説明コメント追加

**Labels**: enhancement, documentation, priority:medium

**Body**:
```
## 概要
カバレッジレポートの未カバー行（22行）について、コード内コメントで理由を明記する。

## 目的
コード保守性の向上

## 実装内容
未カバー行に以下のようなコメントを追加:

```python
# 例: 行219付近
except json.JSONDecodeError as e:
    # カバレッジ: この行は意図的にテスト対象外
    # 理由: 正常なJSONファイルでは発生しないため
    raise InvalidMappingFormatError(
        f"JSONファイルの解析に失敗しました: {e.msg}",
        details={'path': str(file_path), 'error': str(e)}
    )
```

## 対象行
- 行219: JSONDecodeError詳細メッセージ
- 行233-239: ファイルアクセス権限エラー処理
- 行256, 263, 287, 306: validate_mapping_entry()内のエラーパス
- 行349, 355, 362, 368, 378-380: validate_mapping_data()内のエラーパス
- 行396, 402: defaultフィールド検証のエラーパス
- 行413, 421: 空文字・NULL処理の早期リターン
- 行615-617: execute_pattern_match()の例外ハンドリング
- 行745: detect_unregistered_stores()内の未使用分岐

## 工数目安
1時間

## 優先度
中

## 参照ドキュメント
- report/phase6_integration_verification_report.md（8.3.2節）
- report/step_2_2_completion_report.md（9.2.2節）

## 関連ファイル
- modules/category_logic.py
```

---

## Issue 3: 【低優先度】コードカバレッジの向上（89% → 95%以上）

**Title**: 【低優先度】コードカバレッジの向上（89% → 95%以上）

**Labels**: enhancement, testing, priority:low

**Body**:
```
## 概要
現在89%のコードカバレッジを95%以上に向上させる。

## 現状
- カバレッジ: 89%（目標85%達成済み）
- 未カバー行: 22行（主にエラーハンドリング部分）

## 実装内容
以下の未カバー行のテストを追加:

1. **ファイル権限エラーのテスト（mock使用）**
   - ファイルアクセス権限エラーのシミュレーション

2. **特殊なJSONDecodeErrorケースのテスト**
   - 破損したJSONファイルのテスト

3. **不明なmatch_typeの例外ケースのテスト**
   - 無効なmatch_typeでの動作確認

## 期待される成果
- カバレッジ: 89% → 95%以上
- より包括的なエラーハンドリングテスト

## 工数目安
2-4時間

## 優先度
低（現在のカバレッジで実用上問題なし）

## 推奨実装時期
Phase 7以降（必要に応じて）

## 参照ドキュメント
- report/phase6_integration_verification_report.md（8.2.1節）
- report/step_2_2_completion_report.md（9.2.3節）

## 関連ファイル
- modules/category_logic.py
- tests/unit/test_category_logic_*.py
```

---

## Issue 4: 【低優先度】CI/CDパイプラインへの統合

**Title**: 【低優先度】CI/CDパイプラインへの統合

**Labels**: enhancement, ci-cd, priority:low

**Body**:
```
## 概要
GitHub Actionsでテスト自動実行環境を構築し、継続的な品質保証を実現する。

## 目的
- プルリクエスト時の自動テスト実行
- コードカバレッジの自動計測
- コード品質の継続的な保証

## 実装内容

### 1. GitHub Actions ワークフロー作成
`.github/workflows/test.yml`を作成:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ --cov=modules.category_logic --cov-report=term --cov-report=html
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
```

### 2. PEP 8準拠チェック
```yaml
- name: Check PEP 8
  run: flake8 modules/ --max-line-length=99
```

### 3. 型チェック
```yaml
- name: Type check
  run: mypy modules/
```

## 期待される成果
- 自動テスト実行による品質保証
- カバレッジレポートの可視化
- コードレビューの効率化

## 工数目安
4-8時間

## 優先度
低（プロジェクトの規模に応じて検討）

## 推奨実装時期
プロジェクトが複数人開発体制になった場合

## 参照ドキュメント
- report/step_2_2_completion_report.md（9.2.3節）

## 関連ファイル
- .github/workflows/（新規作成）
- requirements.txt
```

---

## GitHub Issueの作成手順

1. GitHubリポジトリのWebページを開く
2. "Issues"タブをクリック
3. "New issue"ボタンをクリック
4. 上記のテンプレートからTitle、Labels、Bodyをコピー＆ペースト
5. "Submit new issue"ボタンをクリック

## 優先度について

- **優先度: 中（2件）**: 次のフェーズまたは適宜対応
- **優先度: 低（2件）**: 必要に応じて対応

現時点で「優先度: 高」の項目はありません。すべての必須要件は満たされており、Step 2.2は完了しています。

---

**作成日**: 2025年12月11日
**作成者**: Claude Code
