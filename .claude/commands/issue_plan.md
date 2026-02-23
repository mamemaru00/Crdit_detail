---
description: Issue対応の修正計画を作成（labels→担当者案→ブランチ案→実装/テスト計画 / 計画はIssueへコメントで記録）
argument-hint: "Issue番号 または IssueのURL"
allowed-tools: Bash(gh:*), Bash(git:*), Read(*)
---

# Issue修正計画（Plan Only + Issueへ記録）

Issue番号またはURL: $ARGUMENTS

## 目的
- Issueを読み、**修正計画だけ**を作成する（実装・ブランチ作成・テスト実行はしない）
- 決まった内容は **GitHub Issue にコメントとして記録（コミット）** する
- 出力物：担当者案 / PM確認事項 / 実装タスク / 影響範囲 / ブランチ名案 / テスト依頼テンプレ

---

## ラベル→担当者（GitHub login）マッピング（案）
- backend: `backend-code-generator`
- frontend: `frontend-implementation-specialist`
- security: `security-compliance-auditor`
- test: `project-compliance-tester`

## 不明点の確認先（PM）
- PM: `project-orchestrator`
- **要件/受け入れ条件/優先度/範囲/仕様が不明な場合は、必ず PM（project-orchestrator）に確認してから進める**

---

## 手順（Claude Code が行うこと：計画作成＋Issueへ記録）

### 1) Issue内容の確認（読み取り）
1. `gh auth status`
2. `gh issue view "<issueRef>" --json number,title,url,body,labels,assignees`

---

### 2) 担当者「案」の決定（任命はしない）
- labels から担当者候補を算出し、既に任命済みは無視して差分のみ提示
- 任命する場合のコマンド案も併記（※このコマンドは実行しない）

---

### 3) PMへ確認すべき質問（必要なら）
- 該当する不明点があれば質問リストを作成
- PM追加/質問コメントのコマンド案を提示

---

### 4) ブランチ案（作成はしない）
- base: `develop`
- name: `feature/issue-{number}-{slug}`
- 作成コマンド案を提示（※実行しない）

---

### 5) 実装計画
- タスクリスト（チェックリスト）
- 受け入れ条件への紐付け
- 影響範囲
- リスク/注意点

---

### 6) formatter/lint 計画（実行はしない）
- `package.json` scripts を見て、利用可能なコマンド案を列挙

---

### 7) テスト計画（変更点に対して / 基本は依頼）
- **テストは対応した内容に対して行う**
- **基本的に project-compliance-tester に依頼する**
- 依頼コメント案（コピペ用）を作る

---

### 8) 決まった内容を Issue に記録（コミット）
- 上記の「修正計画（Plan）」を 1 つのコメントにまとめて投稿する
  - `gh issue comment "<issueRef>" -b "<Plan全文>"`

※ 投稿前に、コメント内容（Plan全文）を表示してユーザー確認を取る  
※ `--dry-run` は設けない（Plan only だが Issue へ記録するのが目的のため）

---

## 注意事項（厳守）
- このコマンドは **計画作成のみ**（ブランチ作成/実装/整形/テスト実行はしない）
- **不明点は必ず PM（project-orchestrator）に確認してから進める**
- 担当者は「案」を出すだけ（任命は別コマンド/運用で実施）

---

## 最終出力フォーマット（Plan）
- 対象Issue: #<number> <title>
- URL: <url>
- 現在ラベル: [...]
- 現在担当者: [...]
- 担当者案（追加候補のみ）: [...]
- PMへの確認事項（必要なら）:
  - ...
- ブランチ案:
  - base: develop
  - name: <branchName>
- 実装タスク（チェックリスト）:
  - [ ] ...
- 受け入れ条件への対応:
  - 条件A ← タスク: ...
- formatter/lint 計画（コマンド案）:
  - ...
- テスト計画:
  - 範囲: ...
  - コマンド案: ...
  - 依頼先: project-compliance-tester
  - 依頼コメント案: ...
- リスク/注意点:
  - ...