# 公開前チェック結果 — 0.1.0

確認日：2026-10-26。**公開準備完了。** GitHubへの公開・push・Release作成は行っていない。

## 必須事項

| 項目 | 結果 |
|---|---|
| 正式ライセンス | PASS：OSIの[MIT正式本文](https://opensource.org/license/mit)を使用。商用利用・改変・再配布・再販売を許諾。著作権/許諾表示の保持が条件 |
| 著作権表示 | PASS：`Copyright (c) 2026 ねむプロ`。READMEにも`MIT License / © 2026 ねむプロ`を記載 |
| ライセンス同梱 | PASS：rootとインストール用スキル内のLICENSEは同一内容。候補ライセンスファイルは0件 |
| 第三者条件 | PASS：Python標準ライブラリだけを使う独自source。Git/Python/PowerShell/Codexの実行ファイルやpipライブラリは配布しない。詳細はLICENSE-REVIEW.md |
| 導入・認識・read-only | PASS：READMEの実コマンドをZIP展開先から隔離ホームへ実行し、2repoで認識と監査不変性を確認 |
| 保護と撤去 | PASS：39テスト。明示許可・新鮮な証拠・正確な対象を必要とし、未統合/ignored実データ等を保持。成功条件の一部はモックで、実測範囲はTEST-RESULTS.mdに明記 |
| 個人情報と梱包 | PASS：個人用絶対パス・ユーザー名・実メール・典型的秘密値・私的ログ・データ・Git fixture・runtime・リンクを含めない。公開名義「ねむプロ」は指定どおりに含める |
| 元環境・rc2の保護 | PASS：日常スキル・共通設定・rc2全ファイルとZIPのSHA一致。実在プロジェクト・起動先は変更なし |
| 実行条件・費用 | PASS：Windows、Python 3.10+、Git for Windows、Windows PowerShell 5.1、利用可能なCodex。追加APIキー・有料サービス不要。Codex自体のプラン条件は適用 |
| GitHub掲載 | PASS：小規模なsourceのみで通常のファイルサイズ制限以内。Git LFS・Actions・外部公開サービスは不要。実際の公開は未実施 |

**必須の残項目は0件。ライセンスや名義の再承認は不要。** GitHubにはこのフォルダ内のファイルだけを掲載し、上位の作業フォルダやローカル生ログを含めない。

## 任意

CI、署名、プラグイン包装、追加のWindows/Python/Codex版や他OSの検証。現在の手動導入版の公開条件にはしない。

## 未確認・対応範囲

別PC・別WindowsアカウントのUSER scopeでの実導入、全Codex版、他OS、Codex管理worktreeの実アーカイブは未実測。取得不能・所有不明の場合は保持する。詳細は[最終テスト報告](TEST-RESULTS.md)。これらを今回の必須検証完了や全環境保証と混同しない。

## GitHub掲載用ファイル一覧

```text
.gitignore
LICENSE
LICENSE-REVIEW.md
PRE-PUBLISH.md
README.md
SHA256SUMS
TEST-RESULTS.md
test-results.json
development-cleanup/
  LICENSE
  SKILL.md
  agents/openai.yaml
  references/execution.md
  scripts/cleanup.py
tests/
  test_cleanup.py
  test_new_profile.py
  test_zip_install.py
```
