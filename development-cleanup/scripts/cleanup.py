"""Conservative Windows cleanup. Audit never writes; apply needs fresh reviewed evidence."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode = True
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')

def canon(p):
    return os.path.normcase(os.path.abspath(p))

def inside(p, root):
    try:
        logical = os.path.commonpath([canon(p), canon(root)]) == canon(root)
        physical_p=canon(os.path.realpath(p)); physical_root=canon(os.path.realpath(root))
        return logical or os.path.commonpath([physical_p,physical_root]) == physical_root
    except ValueError:
        return False

def sha(value):
    return hashlib.sha256(value).hexdigest()

def git(repo, *args, optional=False):
    redirect_keys=('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE',
                   'GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_CONFIG','GIT_CONFIG_PARAMETERS')
    if any(ENV.get(key) for key in redirect_keys) or ENV.get('GIT_CONFIG_COUNT','0') not in ('','0'):
        raise RuntimeError('Git参照先・設定を上書きする環境変数があるため自動判断を保留')
    if args and (args[0] in {'status','diff'} or args[:2]==('worktree','remove')):
        filters=subprocess.run(['git','--no-optional-locks','-C',str(repo),'config','--null',
                                '--get-regexp',r'^filter\..*\.(clean|process)$'],
                               env=ENV,capture_output=True,timeout=30)
        if filters.returncode not in {0,1}:
            raise RuntimeError('Gitフィルター設定を確認できないため保留')
        if filters.stdout:
            raise RuntimeError('外部Git clean/processフィルターを自動実行しないため保留')
    p = subprocess.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'safe.directory='+str(repo), '-C', str(repo), *args],
                       env=ENV, capture_output=True, timeout=120)
    if p.returncode and not optional:
        raise RuntimeError(p.stderr.decode('utf-8', 'replace').strip())
    return p.stdout.decode('utf-8', 'replace') if p.returncode == 0 else None


def resolve_repo(path=None):
    """Detect from the caller's directory, never from a removal target."""
    start=canon(path or os.getcwd())
    if not os.path.isdir(start):raise RuntimeError('Git作業場所が存在しない')
    root=git(start,'rev-parse','--show-toplevel').strip()
    if not root:raise RuntimeError('Git作業ツリーを検出できないため保留')
    return canon(root)

def worktrees(repo):
    rows=[]; row={}
    for field in git(repo, 'worktree', 'list', '--porcelain', '-z').split('\0'):
        if not field:
            if row: rows.append(row); row={}
            continue
        k, _, v = field.partition(' '); row[k]=v
    if row: rows.append(row)
    return rows

def main_state(repo):
    return {'head': git(repo,'rev-parse','HEAD').strip(),
            'branch': git(repo,'rev-parse','--abbrev-ref','HEAD').strip(),
            'refs': git(repo,'for-each-ref','--format=%(refname) %(objectname)'),
            'status': git(repo,'status','--porcelain=v1','-z','--untracked-files=all'),
            'diff': sha(git(repo,'diff','--no-ext-diff','--no-textconv','--binary').encode()),
            'index_diff': sha(git(repo,'diff','--cached','--no-ext-diff','--no-textconv','--binary').encode())}

def tree(path):
    files=[]; dirs=[]; links=[]
    if canon(os.path.realpath(path)) != canon(path):
        raise RuntimeError('リンクを含む解決パス')
    stack=[path]
    while stack:
        p=stack.pop(); st=os.lstat(p); rel=os.path.relpath(p,path)
        if os.path.islink(p) or getattr(st,'st_file_attributes',0) & 1024:
            links.append(rel); continue
        if os.path.isdir(p):
            dirs.append(rel)
            with os.scandir(p) as entries: stack.extend(e.path for e in entries)
        elif os.path.isfile(p):
            h=hashlib.sha256()
            with open(p,'rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
            last=os.lstat(p)
            if (st.st_size,st.st_mtime_ns)!=(last.st_size,last.st_mtime_ns):
                raise RuntimeError('確認中に内容が変化')
            files.append((rel,st.st_size,h.hexdigest()))
        else:
            raise RuntimeError('未対応のfilesystem entry')
    digest=sha(json.dumps([sorted(files),sorted(dirs),sorted(links)],ensure_ascii=False).encode())
    return {'fingerprint':digest,'files':len(files),'bytes':sum(x[1] for x in files),'links':links,
            'nested_git':[d for d in dirs if d!='.' and '.git' in Path(d).parts]}

def cache_file(path, target):
    p=path.replace('\\','/'); parts=p.split('/')
    if '__pycache__' in parts and p.endswith('.pyc'):
        parent=Path(target).joinpath(*parts[:parts.index('__pycache__')])
        source=parts[-1].split('.')[0]+'.py'
        return (parent/source).is_file()
    if p.startswith('.pytest_cache/'):
        return p in {'.pytest_cache/.gitignore','.pytest_cache/CACHEDIR.TAG','.pytest_cache/README.md',
                     '.pytest_cache/v/cache/nodeids','.pytest_cache/v/cache/lastfailed','.pytest_cache/v/cache/stepwise'}
    if p.startswith('.mypy_cache/'):
        return p.endswith(('.data.json','.meta.json','/@plugins_snapshot.json','/CACHEDIR.TAG','/.gitignore'))
    if p.startswith('.ruff_cache/'):
        return p.endswith(('.gitignore','CACHEDIR.TAG')) or bool(re.fullmatch(r'\.ruff_cache/[0-9.]+/\d+',p))
    return False

def evaluate_processes(records, target, own_pid):
    """Missing process fields are unknown, rather than proof of no reference."""
    by_pid={int(p['ProcessId']):p for p in records}
    ancestors=set(); pid=own_pid
    while pid and pid not in ancestors:
        ancestors.add(pid); pid=int(by_pid.get(pid,{}).get('ParentProcessId') or 0)
    target=canon(target).replace('/','\\').lower()
    hits=[]; unknown=[]
    for p in records:
        pid=int(p['ProcessId'])
        if pid in {0,4}:continue  # Windows idle/kernel pseudo-processes.
        exe=(p.get('ExecutablePath') or '').replace('/','\\').lower()
        cmd=(p.get('CommandLine') or '').replace('/','\\').lower()
        if target in exe or (pid not in ancestors and target in cmd):hits.append(pid)
        if not exe or (pid not in ancestors and not cmd):unknown.append(pid)
    return {'known':not unknown,'pids':hits,'uninspectable_pids':unknown,
            'reason':'プロセス情報の取得不足' if unknown else None}


def process_refs(target):
    if os.name!='nt':
        return {'known':False,'pids':[],'reason':'Windowsプロセス確認が必要'}
    command = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $a=@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine); ConvertTo-Json -InputObject $a -Compress"
    p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],
                     env=dict(ENV,DEV_CLEANUP_TARGET=target,DEV_CLEANUP_PID=str(os.getpid())),capture_output=True,timeout=45,
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode: return {'known':False,'pids':[],'reason':'プロセス取得失敗'}
    try: return evaluate_processes(json.loads(p.stdout.decode('utf-8-sig')),target,os.getpid())
    except Exception: return {'known':False,'pids':[],'reason':'プロセス結果不明'}

def reference_hits(target, roots, excludes):
    hits=[]; errors=[]
    exts={'.py','.ps1','.bat','.cmd','.vbs','.json','.toml','.yaml','.yml','.js','.ts','.cs','.code-workspace'}
    skip={'.git','node_modules','.venv','venv','__pycache__','build','dist','.cache','.uv-cache','.acceptance'}
    pattern=re.compile(re.escape(target)+r'(?:[\\\s"\'`]|$)',re.I)
    for root in roots:
        if not os.path.isdir(root): errors.append(str(root)); continue
        for p,ds,fs in os.walk(root,followlinks=False,onerror=lambda e:errors.append(str(e))):
            ds[:]=[d for d in ds if d not in skip and not os.path.islink(os.path.join(p,d))
                   and not getattr(os.lstat(os.path.join(p,d)),'st_file_attributes',0)&1024
                   and not inside(os.path.join(p,d),target)]
            for f in fs:
                q=os.path.join(p,f)
                if canon(q) in excludes or inside(q,target) or Path(q).suffix.lower() not in exts:continue
                try:
                    st=os.lstat(q)
                    if os.path.islink(q) or getattr(st,'st_file_attributes',0)&1024:
                        errors.append('参照スキャンのリンク: '+q);continue
                    if st.st_size>2*1024*1024:
                        errors.append('参照スキャンのサイズ上限超過: '+q);continue
                    raw=Path(q).read_bytes()
                    if raw.startswith((b'\xff\xfe\x00\x00',b'\x00\x00\xfe\xff')):text=raw.decode('utf-32')
                    elif raw.startswith((b'\xff\xfe',b'\xfe\xff')):text=raw.decode('utf-16')
                    else:text=raw.decode('utf-8-sig')
                    if '\0' in text:raise ValueError('不明なテキスト形式')
                    text=text.replace('\\\\','\\').replace('/','\\')
                    if pattern.search(text):hits.append(q)
                except (OSError,UnicodeError,ValueError) as e:errors.append('参照読取不明: '+q+' ('+type(e).__name__+')')
    return {'hits':hits,'errors':errors,'limited_text_scan':True}

def inspect(repo, target, kind='worktree', review=None, reference_roots=(), excluded=()):
    repo=canon(repo); target=canon(target)
    rows=worktrees(repo); main=canon(rows[0]['worktree'])
    if canon(git(repo,'rev-parse','--show-toplevel').strip())!=repo:
        raise RuntimeError('--repoは実rootを指定')
    s={'target':target,'kind':kind,'main':main,'classification':'未確認','reasons':[],'exists':os.path.lexists(target)}
    row=next((x for x in rows if canon(x['worktree'])==target),None)
    if not s['exists']:
        s['classification']='整理不要' if not row else '未確認'
        s['reasons']=['既に不存在・未登録' if not row else '登録だけ残存。pruneしない']
        return s
    def hold(message, mandatory=False):
        s['reasons'].append(message)
        if mandatory:s['classification']='必須保管'
    if target==main:hold('本体checkout',True)
    if inside(os.getcwd(),target):hold('現在の実行cwdを含む',True)
    parts=[p.lower() for p in Path(target).parts]
    if ('.codex' in parts and 'worktrees' in parts) or (Path(target)/'.codex-worktree-name').exists():
        hold('Codex管理領域。正規アプリ整理を使う')
    common=git(main,'rev-parse','--path-format=absolute','--git-common-dir').strip()
    base=git(main,'rev-parse','HEAD').strip()
    s['basis']={'target':target,'kind':kind,'common':canon(common),'base_head':base,'head':None,'git_dir':None}
    if kind=='worktree':
        if not row or not (Path(target)/'.git').is_file():hold('登録linked worktreeでない。独立clone/本体/通常folderは撤去しない',True)
        else:
            actual=git(target,'rev-parse','--path-format=absolute','--git-common-dir').strip()
            if canon(actual)!=canon(common):hold('共通Git不一致',True)
            s['basis']['head']=git(target,'rev-parse','HEAD').strip()
            actual_root=git(target,'rev-parse','--show-toplevel').strip()
            admin=git(target,'rev-parse','--path-format=absolute','--git-dir').strip()
            s['basis']['git_dir']=canon(admin)
            if canon(actual_root)!=target or s['basis']['head']!=row.get('HEAD'):
                hold('targetの実root/HEADと登録が不一致',True)
            backlink=(Path(admin)/'gitdir').read_text(encoding='utf-8').strip()
            if not inside(admin,Path(common)/'worktrees') or canon(os.path.join(admin,backlink))!=canon(Path(target)/'.git'):
                hold('worktree管理gitdirの対応が不一致',True)
            if 'locked' in row or 'prunable' in row:hold('locked/prunable登録')
            s['status']=git(target,'status','--porcelain=v1','-z','--untracked-files=all')
            if s['status']:hold('未コミット/未追跡変更',True)
            s['unmerged']=int(git(main,'rev-list','--count',base+'..'+s['basis']['head'],'--').strip())
            if s['unmerged']:hold('本体HEADに未統合commit',True)
            flagged=[x for x in git(target,'ls-files','-v').splitlines() if x and (x[0].islower() or x[0]=='S')]
            if flagged:hold('assume-unchanged/skip-worktreeの追跡ファイル',True)
            s['ignored']=[x for x in git(target,'ls-files','--others','--ignored','--exclude-standard','-z').split('\0') if x]
            allowed=set((review or {}).get('ignored_cache_files',[]))
            if any(x not in allowed or not cache_file(x,target) for x in s['ignored']):hold('ignored実データまたは未確認ファイル',True)
    elif kind=='empty':
        if row or target==repo or inside(common,target) or inside(target,common):hold('Git管理に必要な場所',True)
        if not os.path.isdir(target) or os.listdir(target):hold('空フォルダでない',True)
    else:raise RuntimeError('Unsupported kind')
    info=tree(target);s['tree']=info;s['basis']['fingerprint']=info['fingerprint']
    if info['links'] or info['nested_git']:hold('リンクまたは埋込Git。参照先を削除しない',True)
    refs=reference_hits(target,reference_roots,{canon(x) for x in excluded});s['references']=refs
    if refs['hits']:hold('起動/設定/外部ソース参照',True)
    if refs['errors']:hold('外部参照の読取不足')
    proc=process_refs(target);s['processes']=proc
    if not proc['known']:hold('プロセス使用状態が未確認')
    if proc['pids']:hold('実行中プロセス参照',True)
    if not review:hold('所有・他chat・外部参照・成果物の確認票なし')
    else:
        if review.get('basis')!=s['basis']:hold('確認票のpath/HEAD/fingerprintが古い')
        try:
            when=dt.datetime.fromisoformat(review['checked_at'].replace('Z','+00:00'))
            seconds=(dt.datetime.now(dt.timezone.utc)-when).total_seconds()
            if not -30<=seconds<=600:hold('確認票の有効期限外')
        except Exception:hold('確認日時不明')
        active=review.get('active_chat_cwd')
        if not active or not os.path.isabs(active):hold('現在chatのworkspace不明')
        elif inside(active,target):hold('現在chat自身の作業場所',True)
        checks=review.get('checks',{})
        for key,value in {'external_references':'clear','other_chats':'unused','codex_management':'normal','artifacts':'disposable'}.items():
            if checks.get(key)!=value:hold(key+' が安全確認済みでない')
    if not s['reasons']:s['classification']='整理可能'
    return s

def apply(args):
    if not args.authorized:raise RuntimeError('明示的な実行許可に対応する--authorizedが必要')
    review=json.loads(Path(args.review).read_text(encoding='utf-8-sig')) if args.review else None
    before=inspect(args.repo,args.target,args.kind,review,args.reference_root,[args.review] if args.review else [])
    if before['classification']=='整理不要':return {'result':'整理不要','before':before}
    if before['classification']!='整理可能':return {'result':'保留','before':before}
    if not args.record_dir:raise RuntimeError('撤去前記録の保存先が必要')
    record=Path(args.record_dir).absolute()
    if canon(os.path.realpath(record))!=canon(record):raise RuntimeError('記録先がリンク経由')
    if inside(record,args.target):raise RuntimeError('記録先は撤去対象の外に置く')
    if inside(record,before['basis']['common']) or any(inside(record,w['worktree']) for w in worktrees(before['main'])):
        raise RuntimeError('記録先はGitと全checkoutの外に置く')
    record.mkdir(parents=True,exist_ok=False)
    main=before['main'];state_before=main_state(main);registrations_before=worktrees(main)
    payload={'inspection':before,'main':state_before,'worktrees':registrations_before}
    (record/'before.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    fresh=inspect(args.repo,args.target,args.kind,review,args.reference_root,[args.review] if args.review else [])
    if fresh['classification']!='整理可能':return {'result':'保留','before':fresh,'record_dir':str(record)}
    if main_state(main)!=state_before:raise RuntimeError('本体が確認中に変化。撤去中止')
    error=None
    try:
        if args.kind=='worktree':git(main,'worktree','remove','--',canon(args.target))
        else:os.rmdir(canon(args.target))
    except Exception as e:error=str(e)
    state_after=main_state(main);remaining=worktrees(main)
    expected=[w for w in registrations_before if canon(w['worktree'])!=canon(args.target)] if args.kind=='worktree' else registrations_before
    check={'target_absent':not os.path.lexists(args.target),'main_unchanged':state_before==state_after,'registrations_match':remaining==expected}
    if args.kind=='worktree':check['commit_retained']=git(main,'cat-file','-e',before['basis']['head']+'^{commit}',optional=True) is not None
    result={'result':'整理完了' if not error and all(check.values()) else '停止・要確認','checks':check,'error':error,
            'record_dir':str(record),'logical_bytes':before['tree']['bytes'],'main_after':state_after,'worktrees_after':remaining}
    (record/'after.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

def cli():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',nargs='?',default='audit',choices=['audit','apply'])
    p.add_argument('--repo',help='省略時は現在の作業場所からGit rootを検出');p.add_argument('--target')
    p.add_argument('--kind',choices=['worktree','empty'],default='worktree');p.add_argument('--reference-root',action='append',default=[])
    p.add_argument('--review');p.add_argument('--record-dir');p.add_argument('--authorized',action='store_true')
    a=p.parse_args()
    try:
        a.repo=resolve_repo(a.repo)
        if a.mode=='apply':
            if not a.target:raise RuntimeError('正確な単一targetが必要')
            out=apply(a)
        elif a.target:
            review=json.loads(Path(a.review).read_text(encoding='utf-8-sig')) if a.review else None
            out=inspect(a.repo,a.target,a.kind,review,a.reference_root,[a.review] if a.review else [])
        else:
            rows=worktrees(a.repo);current=main_state(a.repo)
            main=current if canon(rows[0]['worktree'])==a.repo else main_state(canon(rows[0]['worktree']))
            out={'result':'整理不要' if len(rows)==1 and not current['status'] else '読取点検',
                 'context':{'repo':a.repo,'head':current['head'],'branch':current['branch'],'status':current['status']},
                 'main':main,'worktrees':rows,
                 'note':'読み取り専用の概要。候補だけを--targetで詳しく確認。所有・外部参照・成果物を別途確認し、不明なら保持。'}
        print(json.dumps(out,ensure_ascii=False,indent=2))
        return 2 if out.get('result')=='停止・要確認' else 0
    except Exception as e:
        print(json.dumps({'result':'未確認・保留','error':str(e)},ensure_ascii=False));return 2

if __name__=='__main__':sys.exit(cli())
