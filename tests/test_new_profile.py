"""Probe a copied skill in a synthetic Windows home; never starts a model turn."""
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading

sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parents[1]


def snapshot(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file()}


def main():
    cli = shutil.which('codex')
    if os.name != 'nt' or not cli:
        print(json.dumps({'pass': None, 'reason': 'Windows and Codex CLI required'}))
        return 2
    root = Path(tempfile.mkdtemp(prefix='development-cleanup-new-profile-'))
    home = root/'home'
    home.mkdir()
    (home/'.codex').mkdir()
    (home/'AppData/Roaming').mkdir(parents=True)
    (home/'AppData/Local').mkdir(parents=True)
    installed = home/'.agents/skills/development-cleanup'
    shutil.copytree(PACKAGE/'development-cleanup', installed)
    temp = home/'temp'
    temp.mkdir()
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home),
               HOMEDRIVE=home.drive, HOMEPATH=str(home)[len(home.drive):],
               CODEX_HOME=str(home/'.codex'), APPDATA=str(home/'AppData/Roaming'),
               LOCALAPPDATA=str(home/'AppData/Local'), TEMP=str(temp), TMP=str(temp),
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_COUNT='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    # Do not pass API keys or cloud credentials to the protocol-only probe.
    for name in list(env):
        if any(term in name.upper() for term in ('TOKEN', 'API_KEY', 'SECRET', 'PASSWORD')):
            del env[name]
    env.pop('GIT_TEMPLATE_DIR', None)
    for name in list(env):
        if name.upper().startswith('GIT_'):
            del env[name]
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_COUNT='0')
    repos = []
    for name in ['project-one', 'project-two']:
        repo = root/name
        repo.mkdir()
        def git(*args):
            subprocess.run(['git', '-C', str(repo), *args], env=env,
                           check=True, capture_output=True, timeout=30)
        git('init', '-b', 'main')
        git('config', 'user.name', 'Fixture')
        git('config', 'user.email', 'fixture@invalid.test')
        (repo/'note.txt').write_text('synthetic fixture\n', encoding='utf-8')
        git('add', '.')
        git('commit', '-m', 'fixture baseline')
        shutil.copytree(installed,repo/'.agents/skills/development-cleanup')
        git('add', '.')
        git('commit','-m','fixture skill installation')
        repos.append(repo)
    checks = {}
    installed_before = snapshot(installed)
    for index, repo in enumerate(repos, 1):
        before = snapshot(repo)
        p = subprocess.run([sys.executable, '-B', '-X', 'utf8',
                            str(installed/'scripts/cleanup.py')],
                           cwd=repo, env=env, capture_output=True, timeout=60)
        checks[f'project_{index}_audit_readonly'] = (
            p.returncode == 0 and json.loads(p.stdout)['result'] == '整理不要'
            and before == snapshot(repo))
    diagnostic = (root/'codex-probe-stderr.log').open('wb')
    p = subprocess.Popen([cli, '--no-daemon', 'app-server', '--stdio'],
                         cwd=home, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=diagnostic,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    lines = queue.Queue()
    def reader():
        for line in p.stdout:
            lines.put(line)
    threading.Thread(target=reader, daemon=True).start()
    def rpc(method, params=None, number=None):
        value = {'method': method}
        if params is not None:
            value['params'] = params
        if number is not None:
            value['id'] = number
        p.stdin.write((json.dumps(value)+'\n').encode())
        p.stdin.flush()
        if number is not None:
            while True:
                value = json.loads(lines.get(timeout=45))
                if value.get('id') == number:
                    if 'error' in value:
                        raise RuntimeError('Codex protocol error')
                    return value['result']
    try:
        rpc('initialize', {'clientInfo': {'name': 'cleanup_distribution_test', 'version': '0.1.0'},
                           'capabilities': {'experimentalApi': True}}, 0)
        rpc('initialized')
        data = rpc('skills/list', {'cwds': list(map(str, repos)), 'forceReload': True}, 1)
        (root/'skills-list.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        for index, repo in enumerate(repos, 1):
            rows = [r for r in data['data'] if Path(r['cwd']) == repo]
            found = [s for row in rows for s in row.get('skills', [])
                     if s.get('name') == 'development-cleanup'
                     and Path(s['path']).resolve() == (repo/'.agents/skills/development-cleanup/SKILL.md').resolve()]
            checks[f'project_{index}_isolated_repo_skill_detected'] = (
                len(found) == 1 and Path(found[0]['path']).resolve() == (repo/'.agents/skills/development-cleanup/SKILL.md').resolve()
                and found[0].get('enabled') is True and found[0].get('scope') == 'repo')
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=10)
        diagnostic.close()
    checks['installed_skill_unchanged'] = installed_before == snapshot(installed)
    checks['no_authentication_copied'] = not (home/'.codex/auth.json').exists()
    result = {'pass': all(checks.values()), 'checks': checks,
              'codex': subprocess.check_output([cli, '--version'], env=env,
                                                stderr=subprocess.DEVNULL).decode().strip(),
              'model_turn_started': False, 'physical_new_account_tested': False}
    result['isolation_note']='Windows user skill root uses the OS profile; environment overrides are insufficient. Candidate discovery tested with fresh repo skill copies and isolated CODEX_HOME.'
    output = os.environ.get('DEVELOPMENT_CLEANUP_PROFILE_RESULT')
    if output:
        Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
