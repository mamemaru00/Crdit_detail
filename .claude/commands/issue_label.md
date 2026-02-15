---
description: "Issue内容からカテゴリ判定してラベル付け（backend/frontend/security/test）＋手動 add/remove（既存ラベルは無視）"
argument-hint: "<Issue番号|Issue URL> [--yes] [--dry-run] [--add ラベル1,ラベル2] [--remove ラベル1,ラベル2]"
allowed-tools: Bash(gh:*), Bash(git:*), Read(*)
---

# gitissue-label（自動判定 + 手動操作 / 既存ラベルは無視）

入力: $ARGUMENTS

## 目的
- Issueの title/body を見て、以下のカテゴリを判定して **ラベルを追加** する
  - backend / frontend / security / test
- 追加で、手動 `--add/--remove` もできる
- **すでに付いているラベルは無視**（追加対象から除外し、`gh issue edit --add-label` に渡さない）
- デフォルトは **提案 → 確認 → 実行**
  - `--yes` で確認なし
  - `--dry-run` で実行せず表示のみ

---

## 設定（リポジトリのラベル名に合わせて編集）
- backend: `backend`
- frontend: `frontend`
- security: `security`
- test: `test`

---

## 使い方（例）
- 自動判定（確認あり）
  - `/gitissue-label 123`
- 自動判定（確認なし）
  - `/gitissue-label 123 --yes`
- 自動判定（表示だけ）
  - `/gitissue-label 123 --dry-run`
- 手動追加/削除（自動判定も併用）
  - `/gitissue-label 123 --add bug,triage --remove needs-info`
- Issue URL
  - `/gitissue-label https://github.com/OWNER/REPO/issues/123 --yes`

---

## Claude Code が実行する手順

### 1) 認証・前提チェック
- `gh auth status` を実行して認証確認（未認証なら案内）

### 2) 引数パース
`$ARGUMENTS` から抽出:
- `issueRef`（Issue番号 or Issue URL）
- `--yes` / `--dry-run`
- `--add`（カンマ区切り）
- `--remove`（カンマ区切り）

### 3) Issue情報取得（既存ラベル把握が必須）
- `gh issue view "<issueRef>" --json number,title,url,labels,body`

ここから:
- `currentLabels = labels[].name`（**既存ラベル一覧**）

表示:
- 対象: `#<number> <title>`
- URL
- 変更前ラベル: `currentLabels`

### 4) リポジトリのラベル一覧取得（存在チェック）
- `gh label list --limit 200`

---

## 5) 自動判定ロジック（backend / frontend / security / test）
Issue の title/body を読み、候補を出す（最大2〜3）。

### 例: キーワードのヒント
- backend: API / DB / SQL / migration / queue / Laravel / PHP など
- frontend: UI / component / CSS / React / Next.js / Vite など
- security: XSS / CSRF / injection / vuln / permission / secret など
- test: test / spec / PHPUnit / Jest / e2e / CI など

### 判定の出力（必須）
- `autoLabelsCandidate: [...]`
- 理由（各1行）
- 自信度（High/Med/Low）

---

## 6) 追加・削除対象の確定（★既存ラベルは無視）
1. `autoLabelsCandidate`（自動候補）
2. `manualAddLabels`（`--add`）
3. `manualRemoveLabels`（`--remove`）

### 6-1) 正規化
- ラベル名をトリム
- 空要素除去
- 重複排除（大小文字の扱いはリポジトリ運用に合わせる。基本は完全一致でOK）

### 6-2) 既存ラベル差分を取る（この仕様が重要）
- `addLabelsAll = unique(autoLabelsCandidate + manualAddLabels)`
- **`addLabels = addLabelsAll - currentLabels`**
  - すでに付いているものは **完全に除外**（「無視」）
- `removeLabels = manualRemoveLabels`
  - ※削除は `currentLabels` に無いものを指定しても安全だが、必要なら差分で絞ってOK:
    - `removeLabels = manualRemoveLabels ∩ currentLabels`

### 6-3) 何もしない判定
- `addLabels` も `removeLabels` も空なら
  - 「変更なし（既存ラベルと同じ）」として終了

---

## 7) 実行（または dry-run）
- `--dry-run`:
  - 実行予定コマンド（実際に渡すラベルは差分後の `addLabels/removeLabels`）を表示して終了
- 通常:
  - `--yes` が無ければ確認してから実行

### 実行コマンド（差分後のみ渡す）
- 追加がある:
  - `gh issue edit "<issueRef>" --add-label "<label1,label2,...>"`
- 削除がある:
  - `gh issue edit "<issueRef>" --remove-label "<label1,label2,...>"`
- 両方ある場合はまとめてOK:
  - `gh issue edit "<issueRef>" --add-label "..." --remove-label "..."`

---

## 8) 結果表示（必須）
実行後:
- `gh issue view "<issueRef>" --json url,labels`

出力:
- 対象: `#<number> <title>`
- 変更前ラベル: [...]
- 変更内容:
  - add（実行した分のみ）: [...]
  - remove（実行した分のみ）: [...]
- 変更後ラベル: [...]
- Issue URL: <url>
