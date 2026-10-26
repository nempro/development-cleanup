# 最終テスト報告 — development-cleanup 0.1.0

確認日：2026-10-26（Asia/Tokyo）。MIT License / © 2026 ねむプロ。

検証環境：Windows 10.0.26200 / AMD64、Python 3.10.11、git version 2.53.0.windows.2、Windows PowerShell 5.1.26100.9711、codex-cli 0.164.0-alpha.11.1。

## 今回の変更

- rc2を残して別フォルダへコピーし、OSIのMIT正式本文と`Copyright (c) 2026 ねむプロ`をroot/スキル内の同じLICENSEへ収録。候補ライセンスファイルは配布物から除去した。
- READMEと利用条件・公開前チェックを確定内容へ更新。スキルの許可・保留基準は変更していない。
- ZIP検証でWindowsの長いパスにおけるGitのrevision/path判定エラーを再現。`rev-list --count <範囲> --`とする1行の修正を行った。コミットの比較方法・撤去条件は変えていない。修正前は安全側でエラー停止し、データ破棄は起きていない。
- ZIP導入テストを追加。READMEのPowerShellブロックを改行の正規化以外変更せず実行する。検証用fixtureの過剰な入れ子によるGit MAX_PATHエラーは、合成repo用tempを短い独立領域にして解決した。ユーザーのGit/Windows設定は変更していない。

## 結果と実際に検証した範囲

| 確認 | 結果 | 実測と模擬の区別 |
|---|---|---|
| 既存39テスト | PASS：39/39 | ZIPから展開した実際のスクリプト・既存テストを実行。テストの安全基準や件数は変えていない |
| 正常撤去・Git整合性 | PASS | 本物の`git worktree remove`で合成worktreeを撤去。本体HEAD/branch/refs/変更・登録・残るcommitを照合。削除成功ケースのプロセス一覧だけは完全に観測できた状態を示すモック |
| 保留条件 | PASS | 未コミット、未追跡、未統合、ignored実データ、起動参照、所有/管理不明、自己worktree、独立clone、assume-unchanged、core.worktree偽装、junction別名、古い/未知/ない証拠、許可なし等を合成repoで実測 |
| Windowsの実プロセス | PASS | 自分で起動した待機プロセスを日本語・slash/backslashパスで検出。情報取得不足の保留も別テスト。実機の全保護プロセスを可視化して撤去できたとは主張しない |
| 参照・外部処理 | PASS | UTF-8とBOM付きUTF-16の参照検出、文字コード不明・過大ファイルの保留、fsmonitorを起動しないこと、外部Git filterの保留を確認 |
| 初期read-only・自動検出 | PASS | 本体/サブディレクトリ/linked worktreeの検出、非Git/bare/環境変数redirectの保留、`--authorized`だけではauditから撤去へ変わらないことを確認 |
| ZIP展開とREADME導入 | PASS | ZIPを実際に展開し、READMEの実PowerShell手順で一時ホームの`.agents/skills/development-cleanup`へコピー。全5ファイルの一覧・SHA-256が配布スキルと一致し、正式LICENSEも導入された |
| 既存スキル保護 | PASS | 同じREADME手順を再実行すると上書きを拒否し、既存ファイルのSHAが不変。実ユーザーの日常版を置換するテストはしていない |
| 認識・点検 | PASS | 2つの新規合成repoへ導入スキルを配置し、実Codex app-serverのskills/listで正確なpath・repo scope・有効状態を確認。引数なし監査の前後でrepo全ファイルSHA一致。認証コピー・モデル実行なし |
| 形式と保護 | PASS | skill-creatorの形式検証。元の日常スキル4ファイル・共通設定・rc2全ファイルとZIPのSHAが作業前後で一致。実在プロジェクトをテスト対象にしていない |
| 最終梱包 | PASS | 公開用の明示された16ファイルだけを収録。私的ログ、Git metadata、fixture、ランタイム、個人設定、実メール、個人パス、典型的秘密値、リンクの混入なし。全ファイルのSHA256SUMSとZIP内容を照合 |

同梱の[test-results.json](test-results.json)は個人パスを含まない要約。最終ZIPに収録するスキルは、上記ZIPテストに使った5ファイルとSHAで同一性を確認する。最終ZIPでも同じ導入・認識・点検テストを行い、書類を整えた後のコード変更や手順の不整合がないことを確認する。

## 未検証の範囲

WindowsのUSERPROFILE/HOME差替えは本当の別Windowsアカウントではない。READMEのファイル配置は隔離ホームで実際に行ったが、Codexのユーザースキル探索先はOSの実プロファイルを使うため、認識は新規repoへ置いたコピーの正確なpathとrepo scopeで検証した。同名の日常スキルを成功として数えていない。別PC・別アカウント・全Codex版・他OSは未実測。

Codex管理worktreeの実アーカイブ、全OS shortcut・間接参照・全保護プロセスの完全検出は未実施。管理機能・所有・使用・参照が不明なら保持する仕様であり、これを無条件に削除可能と表示していない。追加の実機テストやCIは任意で、今回の公開を妨げる未解決の必須事項ではない。

元環境の生ログや個人AGENTSは同梱しない。機械的な秘密値検査が未知のすべての秘密を検出するとの保証はしない。GitHubへの公開・push・Release作成は未実施。
