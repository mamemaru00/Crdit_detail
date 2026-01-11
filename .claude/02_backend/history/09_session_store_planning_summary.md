# SQLiteセッションストア実装 - 計画策定サマリー

**作成日**: 2025-12-30
**プロジェクト**: イオンカード明細取込システム
**フェーズ**: Phase 3 Session Management Enhancement
**策定者**: プロジェクトオーケストレーター（Claude Code）

---

## エグゼクティブサマリー

### 承認された方針

**SQLiteベースのサーバーサイドセッションストア**を実装し、現在のCritical問題を解決します。

**解決する課題**:
1. **Cookie 4KB制限**: 1000件CSV（約100KB）をセッションに保存できない
2. **クライアント露出**: セッションデータがブラウザに露出
3. **パフォーマンス低下**: 大量データをCookieで送受信

**実装方針**:
- セッションデータをSQLiteに保存
- CookieにはセッションIDのみ保存（約40byte）
- WALモードで同時実行制御
- TTL管理で自動クリーンアップ

---

## 作成ドキュメント一覧

### 1. 実装計画書（主要ドキュメント）

**ファイル名**: `09_session_store_implementation_plan.md`
**パス**: `C:\work\Lesson\個人開発\Crdit_detail\.claude\02_backend\09_session_store_implementation_plan.md`

**内容**:
- 実装概要と背景
- データベース設計（SQLiteスキーマ、WALモード設定）
- モジュール設計（SessionStoreクラス仕様）
- app.py修正設計（6箇所の修正詳細）
- config.py修正設計
- Docker設定修正
- テスト計画（単体/統合/E2E/パフォーマンス）
- 実装フェーズ分割（Phase 1-5）
- リスク管理計画
- 成果物定義
- タイムライン
- 実装完了チェックリスト

**ページ数**: 約50ページ相当

---

### 2. エージェント割り振り指示書

**ファイル名**: `09_session_store_agent_assignment.md`
**パス**: `C:\work\Lesson\個人開発\Crdit_detail\.claude\02_backend\09_session_store_agent_assignment.md`

**内容**:
- backend-code-generatorへの詳細指示
  - Phase 1: modules/session_store.py実装
  - Phase 2: app.py統合（6箇所修正）
  - Phase 3: Docker統合
  - Phase 4: テスト実装
  - Phase 5: ドキュメント作成
- security-compliance-auditorへの指示（オプション）
- project-compliance-testerへの指示（オプション）
- 重要な実装注意事項
- 成果物チェックリスト

**ページ数**: 約30ページ相当

---

### 3. 計画策定サマリー（本ドキュメント）

**ファイル名**: `09_session_store_planning_summary.md`
**パス**: `C:\work\Lesson\個人開発\Crdit_detail\.claude\02_backend\09_session_store_planning_summary.md`

**内容**:
- エグゼクティブサマリー
- 作成ドキュメント一覧
- 実装スコープサマリー
- 実装フェーズサマリー
- エージェント割り振りサマリー
- タイムラインサマリー
- 次のアクション

---

## 実装スコープサマリー

### 新規ファイル（1ファイル）

| ファイル名 | パス | 説明 | 行数（想定） |
|-----------|------|------|------------|
| `session_store.py` | `modules/session_store.py` | SQLiteセッションストアモジュール | 約300行 |
| `test_session_store.py` | `tests/test_session_store.py` | セッションストア単体テスト | 約500行 |

### 修正ファイル（5ファイル）

| ファイル名 | パス | 修正箇所 | 修正内容 |
|-----------|------|---------|---------|
| `app.py` | `app.py` | 9箇所 | セッション書き込み/読み込み置き換え、初期化、クリーンアップ |
| `config.py` | `config.py` | 1箇所 | セッションストア設定追加 |
| `docker-compose.yml` | `docker-compose.yml` | 1箇所 | セッションDBボリューム追加 |
| `Dockerfile` | `Dockerfile` | 1箇所 | セッションディレクトリ作成 |
| `.gitignore` | `.gitignore` | 1箇所 | セッションDBファイル除外 |

### ドキュメントファイル（3ファイル）

| ファイル名 | パス | 説明 |
|-----------|------|------|
| `CLAUDE.md` | `CLAUDE.md` | セッションストア概要追加 |
| `10_session_store_specification.md` | `.claude/02_backend/` | セッションストア仕様書 |
| `11_session_store_implementation_report.md` | `.claude/02_backend/` | 実装完了レポート |

---

## 実装フェーズサマリー

| フェーズ | タスク | 担当エージェント | 想定時間 | 成果物 |
|---------|-------|----------------|---------|--------|
| **Phase 1** | 基盤実装 | backend-code-generator | 2時間 | `modules/session_store.py` |
| **Phase 2** | app.py統合 | backend-code-generator | 1.5時間 | `app.py`, `config.py` |
| **Phase 3** | Docker統合 | backend-code-generator | 1時間 | `docker-compose.yml`, `Dockerfile`, `.gitignore` |
| **Phase 4** | テスト | backend-code-generator + project-compliance-tester | 2時間 | `tests/test_session_store.py`, テストレポート |
| **Phase 5** | ドキュメント | backend-code-generator | 1時間 | CLAUDE.md, 仕様書, レポート |
| **合計** | | | **7.5時間** | |

---

## エージェント割り振りサマリー

### backend-code-generator（主担当）

**担当範囲**: Phase 1-5の全実装

**主要タスク**:
1. `modules/session_store.py` 実装（SessionStoreクラス、全メソッド）
2. `app.py` 修正（セッション書き込み/読み込み置き換え、初期化、クリーンアップ）
3. `config.py` 修正（セッションストア設定追加）
4. Docker設定修正（docker-compose.yml, Dockerfile, .gitignore）
5. テスト実装（単体/統合/E2E/パフォーマンス）
6. ドキュメント作成（仕様書、実装レポート）

**想定工数**: 7.5時間

**参照ドキュメント**:
- `09_session_store_implementation_plan.md`（必読）
- `09_session_store_agent_assignment.md`（詳細指示）
- `CLAUDE.md`（プロジェクトガイド）

---

### security-compliance-auditor（オプション）

**担当範囲**: Phase 3後のセキュリティレビュー

**主要タスク**:
1. SQLiteファイルパーミッション確認
2. セッションID生成のランダム性確認
3. セッションデータの機密性確認
4. `.gitignore` 設定確認

**想定工数**: 0.5時間

**参照ドキュメント**:
- `09_session_store_implementation_plan.md`（11. リスク管理計画）
- `09_session_store_agent_assignment.md`（セキュリティレビュー指示）

---

### project-compliance-tester（オプション）

**担当範囲**: Phase 4のE2E・パフォーマンステスト

**主要タスク**:
1. E2Eテスト実施（通常フロー、複数ワーカー、WAL肥大化、TTL有効期限）
2. パフォーマンステスト実施（保存/読み込み性能、クリーンアップ性能、同時アクセス）
3. テスト結果レポート作成

**想定工数**: 1時間

**参照ドキュメント**:
- `09_session_store_implementation_plan.md`（8. テスト計画）
- `09_session_store_agent_assignment.md`（E2E・パフォーマンステスト指示）

---

## タイムラインサマリー

```
開始: 2025-12-30（ユーザー承認後）
完了予定: 2025-12-30（7.5時間後）

Phase 1: 基盤実装          [2時間]  ============
Phase 2: app.py統合        [1.5時間] =========
Phase 3: Docker統合        [1時間]  ======
Phase 4: テスト            [2時間]  ============
Phase 5: ドキュメント      [1時間]  ======
                          ─────────────────────
合計                       [7.5時間]
```

---

## 実装計画の特徴

### 1. 詳細性

**実装計画書（50ページ相当）**:
- SQLiteスキーマ定義（SQL文レベル）
- WALモード設定（PRAGMA文レベル）
- SessionStoreクラス仕様（メソッドシグネチャ、docstringレベル）
- app.py修正箇所（行番号、修正前/修正後コードレベル）
- テスト計画（21テストケース詳細）

### 2. 実行可能性

**エージェント割り振り指示書（30ページ相当）**:
- backend-code-generatorへの具体的コード例
- 実装順序の明確化（Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5）
- 成果物チェックリスト（35項目）
- 重要な実装注意事項（6項目）

### 3. リスク管理

**リスク管理計画**:
- ファイルロック競合対策
- WALファイル肥大化対策
- Windows環境でのロック不安定性対策
- データ破損リスク対策
- 古いセッションデータ蓄積対策

### 4. テスト網羅性

**テスト計画（21テストケース）**:
- 単体テスト（21ケース）
- 統合テスト（5ケース）
- E2Eテスト（4シナリオ）
- パフォーマンステスト（4項目）

---

## 次のアクション

### 1. ユーザー承認

**承認項目**:
- [ ] 実装計画の承認
- [ ] エージェント割り振りの承認
- [ ] タイムラインの承認

### 2. 実装開始

**backend-code-generatorへの指示**:
```
以下のドキュメントを参照してSQLiteセッションストア実装を開始してください：

1. 実装計画書:
   C:\work\Lesson\個人開発\Crdit_detail\.claude\02_backend\09_session_store_implementation_plan.md

2. エージェント割り振り指示書:
   C:\work\Lesson\個人開発\Crdit_detail\.claude\02_backend\09_session_store_agent_assignment.md

Phase 1から順に実装してください。各フェーズ完了時に成果物を報告してください。
```

### 3. 進捗管理

**TodoListで進捗管理**:
- [ ] Phase 1: modules/session_store.py実装
- [ ] Phase 1: SQLiteスキーマ初期化とWALモード設定実装
- [ ] Phase 2: app.pyセッション書き込み箇所修正（3箇所）
- [ ] Phase 2: app.pyセッション読み込み箇所修正（3箇所）
- [ ] Phase 2: app.py初期化・クリーンアップ・削除処理追加
- [ ] Phase 2: config.pyセッションストア設定追加
- [ ] Phase 3: docker-compose.ymlセッションDBボリューム追加
- [ ] Phase 3: Dockerfileセッションディレクトリ作成追加
- [ ] Phase 3: .gitignoreセッションDBファイル除外追加
- [ ] Phase 4: tests/test_session_store.py単体テスト実装（全21ケース）
- [ ] Phase 4: 統合テスト・E2Eテスト・パフォーマンステスト実施
- [ ] Phase 5: CLAUDE.md更新
- [ ] Phase 5: 10_session_store_specification.md作成
- [ ] Phase 5: 11_session_store_implementation_report.md作成

---

## プロジェクト全体への影響

### ポジティブな影響

1. **スケーラビリティ向上**:
   - 1000件以上のCSVデータも処理可能
   - Cookie制限に依存しないアーキテクチャ

2. **セキュリティ強化**:
   - セッションデータがクライアントに露出しない
   - サーバーサイドでセッション管理

3. **パフォーマンス改善**:
   - Cookieサイズ削減（100KB → 40byte）
   - ネットワークオーバーヘッド削減

4. **メンテナンス性向上**:
   - セッション管理ロジックの一元化（SessionStoreクラス）
   - 自動クリーンアップでストレージ管理

### 考慮すべき影響

1. **複雑性の増加**:
   - SQLiteファイル管理が追加される
   - WALモード設定の理解が必要

2. **ストレージ要件**:
   - セッションDBファイルのディスク容量（最大数百MB程度）
   - WALファイルの肥大化監視

3. **テスト範囲の拡大**:
   - セッションストアの単体テスト追加
   - WAL肥大化テスト、TTL有効期限テスト追加

---

## 品質保証

### コードレビュー

**レビュー項目**:
- [ ] PEP 8準拠
- [ ] 関数・変数名は英語、コメントは日本語
- [ ] エラーハンドリング完備
- [ ] ロギング適切に実装
- [ ] docstring完備

### テスト網羅性

**テストカバレッジ目標**:
- 単体テスト: 90%以上
- 統合テスト: 主要フロー100%
- E2Eテスト: 全シナリオ実施

### パフォーマンス目標

**性能目標**:
- 1000件CSV保存: 100ms以内
- 1000件CSV読み込み: 50ms以内
- クリーンアップ（1000セッション）: 1秒以内
- 同時アクセス（4ワーカー × 10ユーザー）: エラーなし

---

## 結論

### 計画策定の成果

1. **詳細な実装計画書（50ページ相当）**を作成
2. **具体的なエージェント割り振り指示書（30ページ相当）**を作成
3. **実装完了チェックリスト（35項目）**を定義
4. **リスク管理計画**を策定
5. **テスト計画（21テストケース）**を策定

### 実装準備完了

backend-code-generatorは以下のドキュメントを参照することで、即座に実装を開始できます：

- `09_session_store_implementation_plan.md`
- `09_session_store_agent_assignment.md`
- `CLAUDE.md`

### 期待される成果

実装完了後:
- Cookie 4KB制限の完全解決
- 1000件以上のCSVデータ処理可能
- セキュアなセッション管理
- パフォーマンス目標達成（30秒以内で1000件処理）

---

## 承認履歴

- **2025-12-30**: SQLite実装方針承認（ユーザー）
- **2025-12-30**: 実装計画作成完了（プロジェクトオーケストレーター）
- **2025-12-30**: エージェント割り振り完了（プロジェクトオーケストレーター）

---

## 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|-------|
| 2025-12-30 | 1.0 | 初版作成 | Claude Code (Orchestrator) |

---

**END OF DOCUMENT**
