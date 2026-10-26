import sys
sys.dont_write_bytecode=True
import importlib.util
import unittest
import subprocess
import json
import os
for variable in list(os.environ):
    if variable.upper().startswith('GIT_'):os.environ.pop(variable,None)
os.environ['GIT_CONFIG_GLOBAL']=os.devnull
os.environ['GIT_CONFIG_NOSYSTEM']='1'
os.environ['GIT_CONFIG_COUNT']='0'
os.environ.pop('GIT_TEMPLATE_DIR',None)
os.environ['PYTHONUTF8']='1'
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import uuid
from unittest.mock import patch
from contextlib import redirect_stdout
import io

import tempfile
import platform
BASE=Path(tempfile.mkdtemp(prefix='development-cleanup-tests-'))
SKILL=Path(__file__).resolve().parents[1]/'development-cleanup'
spec=importlib.util.spec_from_file_location('development_cleanup',SKILL/'scripts/cleanup.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
ROOT=BASE/('cleanup-fixtures-'+uuid.uuid4().hex[:8]);ROOT.mkdir()

def run_git(p,*a):return c.git(str(p),*a)

class CleanupTests(unittest.TestCase):
    def setUp(self):
        # A fully observed process inventory is controlled for positive removal
        # tests. Real Windows process visibility is checked separately below.
        self.real_process_refs=c.process_refs
        self.process_patch=patch.object(c,'process_refs',return_value={'known':True,'pids':[]})
        self.mock_process_refs=self.process_patch.start();self.addCleanup(self.process_patch.stop)
        self.folder=ROOT/self._testMethodName;self.folder.mkdir()
        self.repo=self.folder/'本体 repo';self.repo.mkdir()
        run_git(self.repo,'init','-b','main')
        run_git(self.repo,'config','user.name','Cleanup Fixture')
        run_git(self.repo,'config','user.email','fixture@invalid.test')
        (self.repo/'app.py').write_text('print("fixture")\n',encoding='utf-8')
        (self.repo/'.gitignore').write_text('__pycache__/\n.pytest_cache/\ndata/*.sqlite\n',encoding='utf-8')
        run_git(self.repo,'add','.');run_git(self.repo,'commit','-m','fixture baseline')
        self.wt=self.folder/'作業 worktree';run_git(self.repo,'worktree','add','-b','done',str(self.wt))

    def review(self,target=None,kind='worktree',**changes):
        target=target or self.wt
        snap=c.inspect(str(self.repo),str(target),kind)
        data={'basis':snap['basis'],'checked_at':datetime.now(timezone.utc).isoformat(),'active_chat_cwd':str(self.repo),
              'checks':{'external_references':'clear','other_chats':'unused','codex_management':'normal','artifacts':'disposable'},'ignored_cache_files':[]}
        data.update(changes)
        p=self.folder/'review.json';p.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        return p

    def apply(self,target=None,kind='worktree',review=None,roots=None,record=None):
        return c.apply(SimpleNamespace(repo=str(self.repo),target=str(target or self.wt),kind=kind,authorized=True,
             review=str(review or self.review(target,kind)),reference_root=[str(x) for x in (roots or [])],
             record_dir=str(record or self.folder/'receipt')))

    def test_01_safe_worktree_remove(self):
        before=c.main_state(str(self.repo));head=run_git(self.wt,'rev-parse','HEAD').strip()
        result=self.apply()
        self.assertEqual(result['result'],'整理完了',result)
        self.assertFalse(self.wt.exists());self.assertEqual(before,c.main_state(str(self.repo)))
        self.assertEqual(run_git(self.repo,'rev-parse','done').strip(),head)
        self.assertEqual(len(c.worktrees(str(self.repo))),1)

    def test_02_uncommitted_hold(self):
        (self.wt/'app.py').write_text('user work\n',encoding='utf-8')
        result=self.apply();self.assertEqual(result['result'],'保留')
        self.assertEqual((self.wt/'app.py').read_text(),'user work\n')

    def test_03_unmerged_hold(self):
        (self.wt/'app.py').write_text('unmerged\n');run_git(self.wt,'add','.');run_git(self.wt,'commit','-m','not merged')
        result=self.apply();self.assertEqual(result['result'],'保留');self.assertEqual(result['before']['unmerged'],1)

    def test_04_ignored_real_data_hold(self):
        (self.wt/'data').mkdir();(self.wt/'data/user.sqlite').write_bytes(b'unique database')
        review=self.review(ignored_cache_files=['data/user.sqlite'])
        result=self.apply(review=review);self.assertEqual(result['result'],'保留')
        self.assertEqual((self.wt/'data/user.sqlite').read_bytes(),b'unique database')

    def test_05_launcher_reference_hold(self):
        refs=self.folder/'launchers';refs.mkdir()
        (refs/'launch.cmd').write_text('@echo off\npython "'+str(self.wt/'app.py')+'"\n')
        result=self.apply(roots=[refs]);self.assertEqual(result['result'],'保留')
        self.assertTrue(result['before']['references']['hits']);self.assertTrue(self.wt.exists())

    def test_06_unknown_codex_management_hold(self):
        r=self.review();data=json.loads(r.read_text());data['checks']['codex_management']='unknown';r.write_text(json.dumps(data))
        result=self.apply(review=r);self.assertEqual(result['result'],'保留');self.assertTrue(self.wt.exists())

    def test_07_independent_clone_hold(self):
        clone=self.folder/'independent clone';run_git(self.repo,'clone','--no-hardlinks',str(self.repo),str(clone))
        result=self.apply(target=clone);self.assertEqual(result['result'],'保留');self.assertTrue((clone/'.git').is_dir())

    def test_08_git_integrity_and_dirty_main_preserved(self):
        (self.repo/'app.py').write_text('unrelated main edit\n')
        (self.repo/'untracked-user.txt').write_text('preserve\n')
        before=c.main_state(str(self.repo));result=self.apply()
        self.assertEqual(result['result'],'整理完了',result);self.assertEqual(before,c.main_state(str(self.repo)))
        run_git(self.repo,'fsck','--no-progress')

    def test_09_repeat_is_noop(self):
        r=self.review();self.assertEqual(self.apply(review=r)['result'],'整理完了')
        refs=run_git(self.repo,'show-ref')
        self.assertEqual(self.apply(review=r)['result'],'整理不要');self.assertEqual(refs,run_git(self.repo,'show-ref'))

    def test_10_cli_from_two_projects_readonly(self):
        second=self.folder/'second project';second.mkdir();run_git(second,'init','-b','main')
        run_git(second,'config','user.name','Fixture');run_git(second,'config','user.email','fixture@invalid.test')
        (second/'note.txt').write_text('fixture');run_git(second,'add','.');run_git(second,'commit','-m','second baseline')
        for repo in [self.repo,second]:
            before=c.tree(str(repo))['fingerprint']
            p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py'),'audit','--repo',str(repo)],cwd=repo,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr);json.loads(p.stdout)
            self.assertEqual(before,c.tree(str(repo))['fingerprint'])

    def test_11_untracked_hold(self):
        (self.wt/'unsaved.txt').write_text('unsaved')
        self.assertEqual(self.apply()['result'],'保留');self.assertTrue((self.wt/'unsaved.txt').exists())

    def test_12_current_chat_self_hold(self):
        r=self.review(active_chat_cwd=str(self.wt))
        self.assertEqual(self.apply(review=r)['result'],'保留');self.assertTrue(self.wt.exists())

    def test_13_running_process_hold(self):
        self.process_patch.stop()
        for target in [str(self.wt),self.wt.as_posix()]:
            proc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)',target],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                result=self.apply();self.assertEqual(result['result'],'保留');self.assertIn(proc.pid,result['before']['processes']['pids'])
            finally:proc.terminate();proc.wait(timeout=10)

    def test_24_incomplete_process_hold(self):
        rows=[{'ProcessId':12345,'ParentProcessId':0,'ExecutablePath':None,'CommandLine':None}]
        self.mock_process_refs.return_value=c.evaluate_processes(rows,str(self.wt),os.getpid())
        result=self.apply();self.assertEqual(result['result'],'保留')
        self.assertFalse(result['before']['processes']['known']);self.assertTrue(self.wt.exists())

    def test_25_actual_process_visibility(self):
        self.process_patch.stop()
        actual=c.process_refs(str(self.wt))
        self.assertIn('known',actual)
        if actual.get('uninspectable_pids'):
            self.assertFalse(actual['known'])
            result=self.apply();self.assertEqual(result['result'],'保留');self.assertTrue(self.wt.exists())

    def test_26_empty_record_inside_target_rejected_before_write(self):
        empty=self.folder/'empty';empty.mkdir()
        with self.assertRaises(RuntimeError):self.apply(target=empty,kind='empty',record=empty/'receipt')
        self.assertEqual(list(empty.iterdir()),[])

    def test_27_audit_does_not_execute_fsmonitor(self):
        marker=self.folder/'fsmonitor-side-effect.txt'
        hook=self.folder/'fsmonitor-hook.sh'
        hook.write_text('#!/bin/sh\nprintf triggered > "'+marker.as_posix()+'"\nprintf "token\\0"\n',encoding='utf-8')
        run_git(self.repo,'config','core.fsmonitor',hook.as_posix())
        control=subprocess.run(['git','-C',str(self.repo),'status','--porcelain'],capture_output=True)
        self.assertEqual(control.returncode,0);self.assertTrue(marker.exists())
        marker.unlink()
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py'),
            'audit','--repo',str(self.repo)],capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertFalse(marker.exists())

    def test_28_external_clean_filter_is_held_without_execution(self):
        marker=self.folder/'filter-side-effect.txt'
        hook=self.folder/'filter-hook.sh'
        hook.write_text('#!/bin/sh\nprintf triggered > "'+marker.as_posix()+'"\ncat\n',encoding='utf-8')
        (self.repo/'.gitattributes').write_text('*.py filter=fixture\n',encoding='utf-8')
        run_git(self.repo,'config','filter.fixture.clean',str(hook))
        (self.repo/'app.py').write_text('force filter evaluation\n',encoding='utf-8')
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py'),
            'audit','--repo',str(self.repo)],capture_output=True)
        self.assertEqual(p.returncode,2);self.assertFalse(marker.exists())
        self.assertEqual(json.loads(p.stdout)['result'],'未確認・保留')

    def test_14_reviewed_cache_removal(self):
        p=self.wt/'__pycache__';p.mkdir();(p/'app.cpython-311.pyc').write_bytes(b'regenerable cache')
        r=self.review(ignored_cache_files=['__pycache__/app.cpython-311.pyc'])
        result=self.apply(review=r);self.assertEqual(result['result'],'整理完了',result)

    def test_15_stale_review_hold(self):
        r=self.review();(self.wt/'untracked.txt').write_text('new work')
        self.assertEqual(self.apply(review=r)['result'],'保留');self.assertTrue(self.wt.exists())

    def test_16_empty_folder_nonrecursive(self):
        empty=self.folder/'empty folder';empty.mkdir()
        result=self.apply(target=empty,kind='empty');self.assertEqual(result['result'],'整理完了',result)
        self.assertFalse(empty.exists())

    def test_17_codex_path_cannot_be_forged_normal(self):
        managed=self.folder/'.codex/worktrees/managed';managed.parent.mkdir(parents=True)
        run_git(self.repo,'worktree','add','-b','managed',str(managed))
        self.assertEqual(self.apply(target=managed)['result'],'保留');self.assertTrue(managed.exists())

    def test_18_assume_unchanged_hidden_edit_hold(self):
        run_git(self.wt,'update-index','--assume-unchanged','app.py');(self.wt/'app.py').write_text('hidden user edit')
        self.assertEqual(run_git(self.wt,'status','--porcelain').strip(),'')
        self.assertEqual(self.apply()['result'],'保留');self.assertEqual((self.wt/'app.py').read_text(),'hidden user edit')

    def test_19_redirected_core_worktree_hold(self):
        redirected=self.folder/'redirected';redirected.mkdir()
        for name in ['app.py','.gitignore']:(redirected/name).write_bytes((self.wt/name).read_bytes())
        run_git(self.repo,'config','extensions.worktreeConfig','true')
        run_git(self.wt,'config','--worktree','core.worktree',str(redirected))
        (self.wt/'app.py').write_text('preserve actual target data')
        self.assertEqual(run_git(self.wt,'status','--porcelain').strip(),'')
        result=self.apply();self.assertEqual(result['result'],'保留')
        self.assertTrue(any('実root/HEAD' in r for r in result['before']['reasons']))
        self.assertEqual((self.wt/'app.py').read_text(),'preserve actual target data')

    def test_21_no_explicit_authorization(self):
        before=c.tree(str(self.wt))['fingerprint']
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py'),
            'apply','--repo',str(self.repo),'--target',str(self.wt)],capture_output=True)
        self.assertEqual(p.returncode,2)
        self.assertEqual(before,c.tree(str(self.wt))['fingerprint'])

    def test_22_unknown_review_is_not_permission(self):
        checks=dict.fromkeys(['external_references','other_chats','codex_management','artifacts'],'unknown')
        result=self.apply(review=self.review(checks=checks))
        self.assertEqual(result['result'],'保留');self.assertTrue(self.wt.exists())

    def test_23_no_review_no_deletion(self):
        result=c.apply(SimpleNamespace(repo=str(self.repo),target=str(self.wt),kind='worktree',
            authorized=True,review=None,reference_root=[],record_dir=str(self.folder/'receipt')))
        self.assertEqual(result['result'],'保留');self.assertTrue(self.wt.exists())

    def test_29_auto_detect_subdirectory_readonly(self):
        sub=self.repo/'nested';sub.mkdir()
        before=c.tree(str(self.repo))['fingerprint']
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py')],cwd=sub,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        out=json.loads(p.stdout);self.assertEqual(out['context']['repo'],c.canon(self.repo))
        self.assertEqual(out['context']['branch'],'main')
        self.assertEqual(before,c.tree(str(self.repo))['fingerprint']);self.assertTrue(self.wt.exists())

    def test_30_auto_detect_linked_worktree_context(self):
        sub=self.wt/'nested';sub.mkdir()
        before=c.tree(str(self.wt))['fingerprint']
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py')],cwd=sub,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr);out=json.loads(p.stdout)
        self.assertEqual(out['context']['repo'],c.canon(self.wt));self.assertEqual(out['context']['branch'],'done')
        self.assertEqual(before,c.tree(str(self.wt))['fingerprint'])

    def test_31_outside_git_hold_without_guessing(self):
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py')],cwd=self.folder,capture_output=True)
        self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stdout)['result'],'未確認・保留')
        self.assertTrue(self.wt.exists())

    def test_32_bare_repository_hold(self):
        bare=self.folder/'bare.git';run_git(self.repo,'init','--bare',str(bare))
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py'),'--repo',str(bare)],capture_output=True)
        self.assertEqual(p.returncode,2);self.assertTrue(self.wt.exists())

    def test_33_repository_environment_redirect_hold(self):
        with patch.dict(c.ENV,{'GIT_INDEX_FILE':str(self.folder/'external-index')}):
            with self.assertRaises(RuntimeError):c.resolve_repo(str(self.repo))
        self.assertFalse((self.folder/'external-index').exists());self.assertTrue(self.wt.exists())

    def test_34_authorized_flag_does_not_change_default_audit(self):
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py'),'--authorized'],cwd=self.repo,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['result'],'読取点検')
        self.assertTrue(self.wt.exists())

    def test_35_auto_detect_explicit_apply(self):
        review=self.review();before=c.main_state(str(self.repo));old=os.getcwd()
        try:
            os.chdir(self.repo)
            with patch.object(sys,'argv',['cleanup.py','apply','--authorized','--target',str(self.wt),
                    '--review',str(review),'--record-dir',str(self.folder/'receipt')]),redirect_stdout(io.StringIO()) as output:
                code=c.cli()
            self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['result'],'整理完了')
            self.assertFalse(self.wt.exists());self.assertEqual(before,c.main_state(str(self.repo)))
        finally:os.chdir(old)

    def test_36_default_audit_reports_dirty_context(self):
        (self.repo/'app.py').write_text('pending work\n',encoding='utf-8')
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts/cleanup.py')],cwd=self.repo,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('app.py',json.loads(p.stdout)['context']['status']);self.assertTrue(self.wt.exists())

    def test_37_utf16_launch_reference_hold(self):
        refs=self.folder/'launchers';refs.mkdir()
        (refs/'launch.ps1').write_text('python "'+str(self.wt/'app.py')+'"\n',encoding='utf-16')
        result=self.apply(roots=[refs]);self.assertEqual(result['result'],'保留')
        self.assertTrue(result['before']['references']['hits']);self.assertTrue(self.wt.exists())

    def test_38_unknown_encoding_reference_hold(self):
        refs=self.folder/'launchers';refs.mkdir();(refs/'launch.cmd').write_bytes(b'\x81')
        result=self.apply(roots=[refs]);self.assertEqual(result['result'],'保留')
        self.assertTrue(result['before']['references']['errors']);self.assertTrue(self.wt.exists())

    def test_39_oversized_reference_hold(self):
        refs=self.folder/'launchers';refs.mkdir();(refs/'launch.ps1').write_bytes(b' '*(2*1024*1024+1))
        result=self.apply(roots=[refs]);self.assertEqual(result['result'],'保留')
        self.assertTrue(result['before']['references']['errors']);self.assertTrue(self.wt.exists())

    def test_20_alias_current_chat_hold(self):
        alias=self.folder/'chat alias'
        p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
            "New-Item -ItemType Junction -Path $env:CLEANUP_TEST_ALIAS -Target $env:CLEANUP_TEST_TARGET | Out-Null"],
            env=dict(os.environ,CLEANUP_TEST_ALIAS=str(alias),CLEANUP_TEST_TARGET=str(self.wt)),capture_output=True,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(p.returncode,0,p.stderr)
        r=self.review(active_chat_cwd=str(alias))
        result=self.apply(review=r);self.assertEqual(result['result'],'保留')
        self.assertTrue(self.wt.exists());self.assertTrue((alias/'app.py').exists())

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CleanupTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    evidence={'fixture_root':str(ROOT),'tests_run':result.testsRun,'pass':result.wasSuccessful(),
              'failures':[str(t) for t,_ in result.failures],'errors':[str(t) for t,_ in result.errors]}
    evidence.pop('fixture_root',None)
    evidence.update(python=platform.python_version(),platform=platform.system(),git=c.git(str(ROOT/'test_01_safe_worktree_remove'/'本体 repo'),'--version').strip())
    result_path=os.environ.get('DEVELOPMENT_CLEANUP_TEST_RESULT')
    if result_path:Path(result_path).write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False));sys.exit(0 if result.wasSuccessful() else 1)
