---
description: IssueのPlanコメント（修正計画）を元に修正を実施（labels→担当者任命→ブランチ作成→実装→整形→テスト依頼 / git commitなし）
argument-hint: "Issue番号 または IssueのURL [--yes] [--dry-run] [--assign-only] [--skip-assign] [--plan-tag <文字列>]"
allowed-tools: Bash(gh:*), Bash(git:*), Bash(npm:*), Bash(pnpm:*), Bash(yarn:*), Read(*)
---

# Issue対応修正（Planコメント起点）

Issue番号またはURL: $ARGUMENTS

## 目的
- Issue本文ではなく、**Issueコメントに保存された「修正計画（Plan）」を元に**開発を進める
- labelsに応じて担当者を任命 → ブランチ作成 → 実装 → formatter/lint → テスト依頼 → サマリー
- **git commit は行わない**（コミット/PRは別コマンド）
- 決まった内容（計画/実装サマリー/テスト依頼）は **GitHub Issueコメントで記録**する

---

## オプション
- `--yes` : 確認プロンプト最小化（ただし仕様が不明なら止めてPM確認）
- `--dry-run` : 実行予定（採用したPlan・ブランチ名・予定コマンド）のみ表示して終了
- `--assign-only` : 担当者任命だけして終了
- `--skip-assign` : 担当者任命をスキップ
- `--plan-tag <文字列>` : Planコメント識別用のタグを指定（デフォルトは `Issue修正計画（Plan` を探索）

---

## ラベル→担当者（GitHub login）マッピング
- backend: `backend-code-generator`
- frontend: `frontend-implementation-specialist`
- security: `security-compliance-auditor`
- test: `project-compliance-tester`

## 不明点の確認先（PM）
- PM: `project-orchestrator`
- **要件/受け入れ条件/優先度/範囲/仕様が不明な場合は、必ず PM（project-orchestrator）に確認してから進める**

---

## 手順（Claude Code が行うこと）

### 1) Issue + コメント（Plan）取得
1. `gh auth status`
2. Issue情報とコメントをJSONで取得
   - `gh issue view "<issueRef>" --json number,title,url,body,labels,assignees,comments`
3. 抽出して表示
   - Issue番号、タイトル、URL
   - labels（`labels[].name`）
   - 現在の担当者（`assignees[].login`）
   - コメント件数

---

### 2) Planコメントを特定（最重要）
1. Plan識別タグ
   - デフォルト探索文字列: `Issue修正計画（Plan`
   - `--plan-tag` があればそれを使う
2. `comments[].body` から **最新（createdAtが最新）の一致コメント**を1つ選ぶ
   - 一致条件（強→弱の順で評価）
     - (強) `Issue修正計画（Plan` を含む かつ `実装タスク` を含む
     - (中) `ブランチ案` を含む
     - (弱) `テスト計画` を含む
3. 見つからない場合
   - 実装は開始しない
   - 「先に Plan 作成コマンドで計画コメントをIssueに残す」よう案内し終了

4. 見つかった Plan を表示（抜粋ではなく本文をそのまま）
   - 「このPlanを元に実装する」ことを明示

---

### 3) Planから実行パラメータを抽出
Planコメント本文から以下を抽出（見つからない場合は補完ルールへ）
- ブランチ
  - base: `develop`（Planにあればそれ優先）
  - name: `feature/issue-{number}-{slug}`（Planに具体名があればそれ優先）
- 実装タスク
  - 「実装タスク（チェックリスト）」配下の項目をタスクリスト化
- 受け入れ条件
  - 「受け入れ条件への対応」等の記載を抽出
- formatter/lint コマンド案（Planにあれば採用）
- テスト計画（範囲/コマンド案/依頼文案）

補完ルール（Planに無い時）
- ブランチ名が無い → 旧ルールで生成（Issue title slug）
- formatter/lint/test コマンドが無い → `package.json` scripts を見て存在するものを選ぶ
- テスト計画が薄い → `git diff` から変更点ベースで最小プランを作る（依頼文も生成）

---

### 4) 不明点チェック → PMに確認（必要なら）
以下に該当する場合は **実装前に必ずPM確認**（`--yes`でも止める）
- Planが曖昧（実装タスクが抽象的、受け入れ条件が不足）
- 破壊的変更の可能性があるのに条件が未定義
- 仕様が複数解釈できる

実施内容:
1. PMが担当者にいなければ追加（既に任命済みは無視）
   - `gh issue edit "<issueRef>" --add-assignee "project-orchestrator"`
2. Issueコメントで質問を残す
   - `gh issue comment "<issueRef>" -b "<質問（箇条書き）>"`
3. 回答待ちとして終了（推測で進めない）

---

### 5) 担当者の任命（既に任命済みは無視）
※ `--skip-assign` の場合はスキップ。

1. `currentLabels = labels[].name`
2. `currentAssignees = assignees[].login`
3. `targetAssigneesAll`（labels→担当者）を生成
4. 差分のみ追加
   - `assigneesToAdd = targetAssigneesAll - currentAssignees`
   - **既に任命済みは除外**
5. `--dry-run` の場合は予定のみ表示して終了
6. 実行（必要なら確認）
   - `gh issue edit "<issueRef>" --add-assignee "<login>" ...`
7. `--assign-only` の場合は終了

---

### 6) ブランチ作成（develop最新化→新規ブランチ）
1. `git status --porcelain`（汚れていたら方針確認）
2. develop最新化
   - `git fetch origin develop`
   - `git checkout develop`
   - `git pull origin develop`
3. Planで決めたブランチ名で作成
   - `git checkout -b "<branchName>"`
4. `--dry-run` の場合は予定のみ表示して終了

---

### 7) 実装（Planのタスクを厳守）
1. Planの「実装タスク」を上から順に実施
2. 変更対象の探索（既存パターン尊重）
3. 実装
4. `git diff` で差分確認（Planの受け入れ条件と照合）
5. 実装完了サマリー（後でIssueコメントに記録するため、箇条書きで準備）

---

### 8) コード整形（formatter/lint）
1. `cat package.json`（scripts確認）
2. Planに記載があるなら優先、無ければ存在するものだけ実行
   - `npm run format` / `npm run lint`
   - `pnpm run format` / `pnpm run lint`
   - `yarn format` / `yarn lint`

---

### 9) テスト（変更点に対して / 基本は依頼）
方針:
- **テストは対応した内容に対して行う**
- **基本的に project-compliance-tester に依頼する**

手順:
1. 変更ファイル一覧
   - `git diff --name-only develop...HEAD`
2. Planの「テスト計画」があればそれを採用、無ければ差分から最小プランを作る
3. `package.json` scripts から実行コマンド候補を確定
4. project-compliance-tester へ依頼（Issueコメントで記録）
   - 必要なら担当者追加（既に任命済みは無視）
     - `gh issue edit "<issueRef>" --add-assignee "project-compliance-tester"`
   - 依頼コメント
     - `gh issue comment "<issueRef>" -b "<テスト依頼（変更概要/テストプラン/コマンド/期待結果/結果返信依頼）>"`

---

### 10) 実装結果をIssueに記録（コミット）
- 実装サマリーを Issueコメントとして投稿する（git commitではない）
  - `gh issue comment "<issueRef>" -b "<実装完了サマリー（ブランチ名/変更概要/変更ファイル/format&lint結果/テスト依頼状況）>"`

---

## 注意事項（厳守）
- **git commit は行わない**
- **不明点は必ず PM（project-orchestrator）に確認してから進める**
- Planコメントを最優先（Issue本文と矛盾する場合はPMへ確認）
- 担当者任命は差分のみ（既に任命済みは無視）

---

## 最終出力フォーマット（実装後）
- 対象Issue: #<number> <title>
- 採用Planコメント: <commentの要約 or 冒頭1行>
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
- Issueへの記録:
  - 実装サマリーコメント投稿: 済
  - テスト依頼コメント投稿: 済
- 次のアクション:
  - ユーザー確認