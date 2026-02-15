---
description: Issueに対応する修正を実施（labels→担当者任命→ブランチ作成→実装→整形→テスト依頼 / コミットなし）
argument-hint: "Issue番号 または IssueのURL [--yes] [--dry-run] [--assign-only] [--skip-assign]"
allowed-tools: Bash(gh:*), Bash(git:*), Bash(npm:*), Bash(pnpm:*), Bash(yarn:*), Read(*)
---

# Issue対応修正（labels→担当者任命つき）

Issue番号またはURL: $ARGUMENTS

## 目的
- Issueを読み、**ラベルに応じて担当者を任命**してから開発を進める
- ブランチ作成 → 実装 → formatter/lint → **変更点に対するテスト（基本は依頼）** → サマリー
- **コミットは行わない**

---

## オプション
- `--yes` : 確認プロンプトを最小化（ただし要件が曖昧なら止めて確認）
- `--dry-run` : 予定手順・予定コマンドのみ表示して終了（実行しない）
- `--assign-only` : 担当者任命だけして終了
- `--skip-assign` : 担当者任命をスキップして、ブランチ作成以降へ

---

## ラベル→担当者（GitHub login）マッピング
- backend: `backend-code-generator`
- frontend: `frontend-implementation-specialist`
- security: `security-compliance-auditor`
- test: `project-compliance-tester`

---

## 不明点の確認先（PM）
- PM: `project-orchestrator`
- **要件/受け入れ条件/優先度/範囲/仕様が不明な場合は、必ず PM（project-orchestrator）に確認してから進める**
  - 例: Issueコメントで質問を投げる（必要なら PM を担当者に追加して依頼）

---

## 手順（Claude Code が行うこと）

### 1) Issue内容の確認（labels/assignees含む）
1. `gh auth status`
2. `gh issue view "<issueRef>" --json number,title,url,body,labels,assignees`
3. 抽出して表示
   - Issue番号、タイトル、URL
   - labels（`labels[].name`）
   - 現在の担当者（`assignees[].login`）
   - 要件/受け入れ条件（明記があれば）

---

### 2) 不明点がある場合の確認（PMへ）
**以下のいずれかに該当したら、実装前に PM（project-orchestrator）へ確認する**
- 受け入れ条件が書かれていない/曖昧
- 期待動作が複数解釈できる
- 影響範囲が広いのにガードが無い（破壊的変更の恐れ）
- 仕様変更が必要そう
- 対応優先度や期限が不明

実施内容（例）:
1. PM が担当者にいなければ、必要に応じて追加（既に任命済みは無視）
   - `gh issue edit "<issueRef>" --add-assignee "project-orchestrator"`
2. Issue コメントで質問を残す
   - `gh issue comment "<issueRef>" -b "<質問（箇条書き）>"`

※ `--yes` でも、仕様が不明確なら止めて確認する（推測で進めない）

---

### 3) 担当者の任命（既に任命済みは無視）
※ `--skip-assign` の場合はスキップ。

1. `currentLabels = labels[].name`
2. `currentAssignees = assignees[].login`
3. `targetAssigneesAll` を生成（labelsに応じて担当者を集める）
4. 差分を取る
   - `assigneesToAdd = targetAssigneesAll - currentAssignees`
   - **既に任命済みは除外（無視）**
5. `assigneesToAdd` が空なら「担当者変更なし」
6. `--dry-run` なら実行予定のみ表示して終了
7. 実行（必要なら確認）
   - `gh issue edit "<issueRef>" --add-assignee "<login>" ...`
8. 再取得して表示
   - `gh issue view "<issueRef>" --json url,assignees,labels`

9. `--assign-only` の場合は終了

---

### 4) ブランチ作成（develop最新化→新規ブランチ）
1. `git status --porcelain`
2. develop最新化
   - `git fetch origin develop`
   - `git checkout develop`
   - `git pull origin develop`
3. ブランチ名: `feature/issue-{number}-{slug}`
4. `--dry-run` の場合は予定のみ表示して終了
5. `git checkout -b "<branchName>"`

---

### 5) 実装（Issue要件に基づく）
1. 変更対象の探索（構成把握/キーワード検索）
2. 実装方針（どこをどう直すか、受け入れ条件への対応）
3. 実装
4. `git diff` で差分確認

---

### 6) コード整形（formatter/lint）
1. `cat package.json`（scripts確認）
2. 存在するものだけ実行
   - `npm run format` / `npm run lint`
   - `pnpm run format` / `pnpm run lint`
   - `yarn format` / `yarn lint`

---

### 7) テスト（変更点に対して実施 / 基本は project-compliance-tester に依頼）
1. 変更ファイル一覧
   - `git diff --name-only develop...HEAD`
2. テストプラン作成（変更点に紐づく範囲）
3. scripts確認（使えるテストコマンドを特定）
   - `cat package.json`
4. project-compliance-tester に依頼（Issueコメントで残す）
   - 必要なら担当者追加（既に任命済みは無視）
     - `gh issue edit "<issueRef>" --add-assignee "project-compliance-tester"`
   - 依頼コメント
     - `gh issue comment "<issueRef>" -b "<テスト依頼（テストプラン/コマンド/期待結果）>"`

---

## 注意事項（厳守）
- **コミットは行わない**
- **不明点は必ず PM（project-orchestrator）に確認してから進める**
- 実装完了後に必ず報告（依頼したテストも含める）
  - 対象Issue / ブランチ
  - 変更概要 / 変更ファイル
  - format/lint の結果
  - テスト：依頼済み/完了、要点
  - 次のアクション（ユーザー確認 → PR作成は別コマンド）

---

## 最終出力フォーマット（実装後）
- 対象Issue: #<number> <title>
- ブランチ: <branchName>
- 変更概要:
  - ...
- 変更ファイル:
  - ...
- 実行結果:
  - format: OK/NG（要点）
  - lint: OK/NG（要点）
- テスト:
  - テストプラン: ...
  - 依頼先: project-compliance-tester
  - 状態: 依頼済み / 完了OK / 完了NG
- 次のアクション:
  - ユーザー確認 → PR作成（別コマンド）
