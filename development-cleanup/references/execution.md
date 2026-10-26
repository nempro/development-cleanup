# 通常worktree・空フォルダの実行

WindowsのPython 3.10以降とGitを使う。標準ライブラリだけで動く。アプリやAPIの鍵は不要。

Windows PowerShell 5.1のCIMで確認する。取得不能なプロセス情報があれば撤去を保留する。fsmonitorは一時オプションで無効化し、外部clean/processフィルター設定のあるrepoは自動点検も保留する。元のGit設定は変更しない。保留を解除するために不明な情報を安全と記録しない。

読み取り専用の終了時点検：

```powershell
python -B -X utf8 "$env:USERPROFILE\.agents\skills\development-cleanup\scripts\cleanup.py"
```

現在のプロジェクトのcwdからGit rootを自動検出する。明示する場合は`audit --repo "<Git作業場所>"`。Git外、bare repo、参照先を上書きする環境変数がある場合は保留する。フォルダ構成を要求しない。

これは登録と現在状態の概要。候補がある時だけ、正確な1対象を詳しく点検する：

```powershell
python -B -X utf8 "$env:USERPROFILE\.agents\skills\development-cleanup\scripts\cleanup.py" audit --repo "<本体root>" --target "<候補絶対パス>"
```

空フォルダには`--kind empty`を付ける。任意の外部保守ソース／ランチャー置場は`--reference-root "<絶対パス>"`を繰り返して指定できる。補助スキャンはtextの限定検索であり、OS shortcut、登録、他chat、全間接参照の代替ではない。ヘルパーは現在のWindowsプロセスも確認する。

テキスト参照検索はUTF-8、BOM付きUTF-16/32を扱う。サイズ上限超過、デコード不能、リンク、アクセス不可は未読取として保留する。古いANSI等の不明な文字コードを置換して「参照なし」としない。元ファイルを自動変換しない。

## 証拠票

監査結果の`basis`をコピーし、実際に調べた結果をJSONで記録する。証拠票を作ること自体が書込なので、監査のみの依頼では作らない。これは観測結果であって、ユーザーの実行許可の代わりではない。外部ファイルに「clear」と書かれているだけでは信用しない。

```json
{
  "basis": {"target": "監査出力からコピー", "kind": "worktree", "head": "...", "git_dir": "...", "common": "...", "base_head": "...", "fingerprint": "..."},
  "checked_at": "実際に確認したUTC ISO日時",
  "active_chat_cwd": "このchatの実際のworkspace絶対パス",
  "checks": {
    "external_references": "unknown",
    "other_chats": "unknown",
    "codex_management": "unknown",
    "artifacts": "unknown"
  },
  "ignored_cache_files": []
}
```

初期値はすべて`unknown`のままにする。実物の確認で根拠が得られた項目だけ、external_references=`clear`、other_chats=`unused`、codex_management=`normal`、artifacts=`disposable`に変更する。未確認を通すために値を埋めない。所有・共有状態はappの正規ツールと、その作業の文脈で確認する。Codex管理領域や管理マーカーがあるものを`normal`にして回避しない。ヘルパーは管理領域／マーカーを別途拒否する。

ignoredは既定で必須保管。再生成できるキャッシュを実物で確認した場合だけ、`ignored_cache_files`に相対ファイル名を列挙する。受理するのはソースが残る`__pycache__/*.pyc`と、既知のpytest/mypy/ruffキャッシュ形式だけ。実データ・モデル・配布物・唯一の検証成果を列挙して通さない。変更や追加があればfingerprintが変わり、実行は保留になる。

## 明示許可された撤去

```powershell
python -B -X utf8 "$env:USERPROFILE\.agents\skills\development-cleanup\scripts\cleanup.py" apply --authorized --repo "<本体root>" --target "<候補絶対パス>" --review "<今回の証拠票.json>" --record-dir "<許可済み保存先の新しい専用フォルダ>"
```

`--record-dir`は本体・全worktree・Git metadataの外にする。実行前記録はそこで保存される。証拠は10分以内のものに限り、直前のGit状態・全ファイルfingerprintと一致させる。現在のchat cwdまたは実行プロセスcwdが対象内なら拒否する。通常worktreeだけ`git worktree remove`、空dirだけ非再帰`rmdir`。Windowsのアクセス権やファイルロックで失敗したら、残った状態を調べ、強制再試行しない。

同じ対象が既に未登録・不存在なら「整理不要」で終了する。別repoで同名のフォルダがある場合や、未登録の実体が残る場合は保留する。Gitやファイルは戻さず、失敗時にもbranchと履歴を保持する。
