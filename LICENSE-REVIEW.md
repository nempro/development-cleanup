# 利用条件・ライセンス確認

確認日：2026-10-26。対象は独自の指示文・Pythonソース・説明書・合成テストのみ。AIの支援で作成した。Python/Git/Windows PowerShell/Codexのバイナリ、第三者pipパッケージ、モデル、素材、個人設定、実データは同梱しない。

## 必須

| 対象 | 確認結果・必要条件 | 根拠 |
|---|---|---|
| Codexスキル仕様 | name/descriptionを持つSKILL.md、agents/openai.yaml、scripts/referencesという構成。USERの`.agents/skills`へ手動配置可能。形式検証と配布コピーの検出を実施。明示/暗黙の選択を維持し、削除の許可は選択とは別に確認する | [公式スキル仕様](https://learn.chatgpt.com/docs/build-skills) |
| 実行環境 | Python 3.10以降の標準ライブラリ、Git for Windows、Windows PowerShell 5.1/CIM、利用可能なCodex。Python/GitはPATHから呼び出す。正確な検証版はTEST-RESULTS.mdに記載 | [Pythonライセンス](https://docs.python.org/3/license.html)、[Windows PowerShellの製品説明](https://learn.microsoft.com/en-us/powershell/scripting/what-is-windows-powershell?view=powershell-5.1) |
| Python | PSF License等。インストール済みの外部ランタイムとして使用し、コード・バイナリは同梱しない。将来同梱する場合は正確な版と構成要素の表示条件を再確認する | [Python公式条件](https://docs.python.org/3/license.html) |
| Git | Git/Git for WindowsのCOPYINGはGPLv2等。外部プログラムを実行するだけを理由に、本独自ソースへGPLを適用しなければならないという条件は確認されない。Git自体や同梱コンポーネントの再配布は今回行わない | [Git COPYING](https://raw.githubusercontent.com/git/git/master/COPYING)、[Windows版COPYING](https://raw.githubusercontent.com/git-for-windows/git/main/COPYING) |
| Windows PowerShell | Windows標準の外部機能を使う。PowerShell 7とは別製品。Windows PowerShellをMITのバイナリとして再配布できるとは扱わない。何も同梱しない | [Microsoft公式説明](https://learn.microsoft.com/en-us/powershell/scripting/what-is-windows-powershell?view=powershell-5.1) |
| 独自部分の再利用許諾 | MITを正式採用。Copyright (c) 2026 ねむプロ。商用利用・改変・再配布・再販売を許諾し、著作権・許諾表示の保持が必要。OSIの正式本文をrootとスキル内の同一LICENSEへ収録した | [MIT原文](https://opensource.org/license/mit)、[正式LICENSE](LICENSE) |
| 公開できる権限 | 公開者が共有可能な内容だけを公開する。OpenAI利用規約における出力の当事者間帰属は法令上認められる範囲であり、入力権利・第三者権利・著作権成立を一律保証するものではない。公開条件はMIT License / © 2026 ねむプロとして確定済み | [OpenAI利用規約](https://openai.com/policies/terms-of-use/)、[GitHub利用規約](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) |
| GitHub無料公開・再配布 | GitHub自体はライセンスの選択を義務付けない。ただし無指定では通常の著作権の扱いとなり、一般的な改変・再配布権を与えない。今回の再利用目的に対し、MIT採用を公開者が確定済み。公開コンテンツには閲覧・fork等のサービス上の許諾も関係する | [GitHubのライセンス説明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)、[利用規約D節](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) |
| GitHubのファイル・秘密情報 | 通常Gitで100MiB超は拒否、ブラウザー追加は25MiB上限。今回の小さなソース配布にGit LFSは不要。完成物のサイズ・秘密情報・個人情報を検査し、テストfixtureやローカル生ログを含めない | [公式サイズ制限](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)、[secret scanningの説明](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning) |
| 外部サービス・課金 | ヘルパーはローカルGit/CIMと標準ライブラリだけ。APIキー・有料サービス・モデル取得は不要。Codexは利用者の契約・プラン・上限に従う。無料スキルはCodexの無料・無制限利用を意味しない。GitHub Freeの公開source hostingを想定し、Actions/LFS/Codespaces等は使わない | [GitHubプラン](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)、[OpenAI利用規約](https://openai.com/policies/terms-of-use/) |

## 任意

- プラグイン包装：公式は複数利用者向け配布にプラグインを推奨する。今回の単一スキルのGitHubソース配布と手動コピーは、ローカルスキルとして利用可能。プラグイン登録・マーケットへの提出は必須にしない。[公式仕様](https://learn.chatgpt.com/docs/build-skills)
- 署名、CI、追加OS対応、追加の実機マトリクス。今回の利用方法に必須の有料サービスや外部問い合わせはない。

## 未確認

- 別PC・別Windowsアカウント・全Codex版の実行。確認した範囲だけを対応確認済みとする。
- 将来選ぶ公開先アカウント・組織固有の制約と適用契約。今回アカウント設定を調査・変更せず、公開もしていない。具体的な制約が判明していないため、架空の審査や承認待ちを課さない。

第三者ライブラリ・ランタイムの再配布はないため、それらのライセンス原文や実行ファイルは添付していない。制作時の形式検証に用いたPyYAMLはテスト用環境だけにあり、配布物・実行依存に含めない。動作テストは標準ライブラリだけで実行できる。

このsource-only構成について、確認した条件から具体的な無料配布の阻害要因は見つからなかった。最終ファイル構成と本確認結果を照合済み。ユーザーの明示指定に従いMITを正式採用した。法的適合性・権利の成立・全環境動作を保証するとの表示はしない。
