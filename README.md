# 開発フォルダお掃除

**development-cleanup 0.1.0** — Windows上のCodexで、開発中に増えたGitワークツリーや一時作業物を安全に点検するスキルです。GitHubで無料公開しています。[公開前チェック結果](PRE-PUBLISH.md)を同梱しています。OpenAIの公式製品・公式スキルではありません。

**MIT License / © 2026 ねむプロ**

初期動作は読み取り専用です。現在の作業場所からGitリポジトリを検出し、利用者が撤去を明示した場合だけ、安全確認済みの対象を個別に片付けます。特定のドライブやフォルダ構成を要求しません。

## 必要なもの

- ユーザースキルを扱えるCodexアプリまたはCLI。
- Windows、Python 3.10以降、Git for Windows、Windows PowerShell 5.1 (`powershell.exe`)。
- PythonとGitをPATHから呼び出せること。ターミナルで`python --version`、`git --version`を実行すると確認できます。

Python標準ライブラリだけを使います。pipパッケージ・追加モデル・APIキーは不要です。ヘルパー自身は通信しません。Codexのモデル処理には利用者の契約・料金・利用上限が適用されます。このスキルのために有料サービスへ新規加入する仕組みはありません。

検証した正確な版は [TEST-RESULTS.md](TEST-RESULTS.md) に記載しています。macOS/Linuxでの撤去は未検証です。Gitの必要な機能やプロセス確認が使えなければ保留します。

## インストール

1. 配布ZIPを展開します。GitHubから入手する場合も、ダウンロードしたZIPを先に展開します。
2. このREADMEがあるフォルダでPowerShellを開き、次を実行します。コピーするのは中の`development-cleanup`フォルダだけです。

```powershell
$sourceSkill = Join-Path $PWD 'development-cleanup'
$skillParent = Join-Path $env:USERPROFILE '.agents\skills'
$destinationSkill = Join-Path $skillParent 'development-cleanup'
if (-not (Test-Path -LiteralPath (Join-Path $sourceSkill 'SKILL.md'))) { throw 'READMEがある展開先で実行してください' }
if (Test-Path -LiteralPath $destinationSkill) { throw '既存スキルがあります。上書きしません' }
New-Item -ItemType Directory -Path $skillParent -Force | Out-Null
Copy-Item -LiteralPath $sourceSkill -Destination $destinationSkill -Recurse
```

3. Codexで対象プロジェクトの新しいチャットを開き、`$development-cleanup`を選択します。候補に出なければCodexを再起動し、`%USERPROFILE%\.agents\skills\development-cleanup\SKILL.md`が存在するか確認します。同名のスキルが別の場所にあると両方が表示されるため、追加先のファイルを確認してください。

ユーザー共通配置と`$名前`による呼び出しは [公式スキル仕様](https://learn.chatgpt.com/docs/build-skills) に基づきます。既存の同名スキルがあれば、この手順は停止します。自動でマージ・更新・上書きはしません。AGENTS.mdやCodex設定の編集は導入の必須条件ではありません。

## 点検だけをする

対象プロジェクトのチャットで依頼します。

```text
$development-cleanup 今回の開発で残した作業場所を読み取り専用で点検してください。ファイルは変更しないでください。
```

Codexは対象のGitルート、branch・HEAD・変更、worktree登録、固有成果、使用・参照状態を必要な範囲で調べます。結果は日本語で「整理不要」「整理可能」「必須保管」「未確認」などとして理由とともに報告します。監査だけの依頼では記録ファイルも作成しません。

ヘルパーを直接使う場合は、対象repoまたはそのサブディレクトリをカレントフォルダにして実行します。引数を省略すると読取点検です。

```powershell
python -B -X utf8 "$env:USERPROFILE\.agents\skills\development-cleanup\scripts\cleanup.py"
```

linked worktreeからも検出し、現在の場所のbranchと本体の状態を区別します。Git外では推測して別フォルダを探さず保留します。別の場所を明示する場合は`audit --repo "<Git作業場所>"`を使えます。複数のrepoを一括探索しません。

## 実際に片付ける

まず点検し、対象を絞って明示します。

```text
$development-cleanup 今回作った通常のGitワークツリーについて、安全と確認できたものだけ後片付けを実行してください。未確認のものは保持し、ブランチとGit履歴を残してください。実行記録は指定した作業記録フォルダに保存してください。
```

Codexは対象ごとの証拠を確認し、普通のlinked worktreeには正式な`git worktree remove`を使用します。Codex自身が管理するworktreeには利用可能なアプリ標準の整理・アーカイブ機能を優先し、正規機能が利用できない場合や所有状態が不明な場合は保留します。

ヘルパーで撤去するには、明示した1対象・10分以内の確認票・`--authorized`・Git/全checkout外の新しい記録先が必要です。詳しいコマンドと確認票は [実行仕様](development-cleanup/references/execution.md) を参照してください。確認票やフラグを付けるだけでは安全確認や利用者の指示の代わりになりません。

終了コード0でも保留・整理不要の場合があります。JSONの`result`と`reasons`を確認してください。失敗時には強制再試行しません。

## 自動で削除しないもの

- 未コミット変更、未追跡ファイル、本体への未統合コミット。
- ignored内の実データ・モデル・設定・配布物・唯一の検証成果。
- 現在のチャット自身、使用中、所有や外部参照が不明なworktree。
- 本体、独立clone、他のプロジェクト、古いという理由だけのフォルダ。
- Codex管理状態が不明な場所、リンク先の内容、非空フォルダの一括削除。

`--force`、`git clean -fdx`、reset、ブランチ・Git履歴の削除、起動先変更は使いません。再生成可能なignoredキャッシュでも、実物を確認し、受理する既知形式の正確なファイルだけを証拠票へ列挙する場合に限ります。実データを許可リストに書いて撤去を通すことはできません。

## 使用上の注意

利用者が管理・信頼しているローカルrepoが対象です。点検はバックアップを代替しません。全OS参照・全ショートカット・他のチャットの状態をヘルパーだけで自動証明するものではなく、Codexが別途確認できなければ保持します。対象全ファイルをSHA計算する場合はデータ量に応じた時間がかかります。

Windowsの保護プロセスなどの情報が取得できない場合、撤去は保留します。管理者実行で必ず解消するとは限りません。取得できない情報を「参照なし」として通しません。Git fsmonitorはコマンド単位で無効化し、外部clean/processフィルター設定があるrepoは起動せず保留します。未使用のGit LFS設定等でも該当します。元の設定は変更しません。GIT_DIR・GIT_INDEX_FILE等で参照先が上書きされている場合も保留します。

参照ファイルはUTF-8とBOM付きUTF-16/32を扱います。2MiB超、文字コード不明、アクセス不可などで読めない場合は未確認として保留します。元ファイルを自動変換しません。

出力や撤去記録にはローカルパス・ファイル名が含まれます。実環境の記録をそのまま公開しないでください。個人のAGENTS.md、認証情報やプロジェクトデータはこの配布物に含めていません。

インストールだけで、すべての開発完了時に確実に起動するものではありません。通常は上記の明示呼び出しを使います。終了時の案内を常用する場合だけ、既存ルールと重複しない場所へ次のような指示を利用者が任意で追加できます。この配布物は設定を自動編集しません。

```text
開発終了時はdevelopment-cleanupで今回の一時作業物を読み取り専用点検する。通常の終了報告は撤去の許可ではない。撤去は明示指示と対象ごとの安全確認がある場合だけ行い、未確認のものは保持する。
```

## アンインストール

1. このスキルを使った処理が終了していることを確認します。
2. エクスプローラーで`%USERPROFILE%\.agents\skills`を開き、今回導入した`development-cleanup`フォルダだけを削除します。親の`.agents`や`skills`全体は削除しません。元からあった別のスキルを今回のものとして扱わないでください。
3. 終了時案内を自分でAGENTS.mdへ追加した場合は、その追加部分だけを削除します。追加していなければ設定変更は不要です。
4. Codexで新しいチャットを開きます。候補が残る場合は再起動し、別scopeの同名スキルがないか確認します。

アンインストールはプロジェクト、Git履歴、worktree、実データ、過去の実行記録を削除する操作ではありません。それらはそのまま残ります。

## 開発者向けテストと配布内容

```powershell
python -B -X utf8 .\tests\test_cleanup.py
python -B -X utf8 .\tests\test_new_profile.py
```

実在プロジェクトを引数に渡さず、配布ルートで実行します。合成repoだけを一時領域へ作成します。利用者のGit設定・環境変数を切り離し、作成者情報は架空値をrepo内へ設定します。解析用の合成fixtureは自動削除しません。 ZIPからの導入を含めて再現する場合は、`python -B -X utf8 .\tests\test_zip_install.py "<信頼できる配布ZIPのパス>" --suite`を実行できます。

削除成功ケースは、プロセスを完全に確認できた状態のモックを使用します。実際のWindowsプロセスの検出・取得不足保留は別ケースです。2つ目のテストはCodex CLIが必要で、隔離CODEX_HOMEと新規repo内のスキルコピーを検査します。Windowsの実ユーザープロファイル探索は環境変数だけでは切り替わらないため、別Windowsアカウントの実機テストではありません。認証コピー・モデル実行は行いません。

GitHubへ掲載するのは、このREADMEがあるフォルダの内容だけです。上位フォルダや個人の作業記録を一緒に公開しないでください。

スキル一式は`development-cleanup/`、検証ソースは`tests/`です。Python・Git・PowerShell・Codexの実行ファイルは同梱しません。[テスト報告](TEST-RESULTS.md)、[利用条件](LICENSE-REVIEW.md)、[公開前の確認事項](PRE-PUBLISH.md)を合わせて確認してください。正式ライセンスは [MIT License](LICENSE) です。商用利用・改変・再配布・再販売が可能で、著作権・許諾表示の保持が必要です。
