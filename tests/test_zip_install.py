"""Test a trusted release ZIP using the actual README installer in a temporary home."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.dont_write_bytecode=True


def snapshot(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip_path',help='Trusted locally built release ZIP')
    parser.add_argument('--suite',action='store_true',help='Also run the 39 safety cases from the extracted ZIP')
    args=parser.parse_args()
    archive=Path(args.zip_path).resolve()
    work=Path(tempfile.mkdtemp(prefix='development-cleanup-zip-test-'))
    extraction=work/'extracted';extraction.mkdir()
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist()
        if len(entries)>200 or sum(i.file_size for i in entries)>10*1024*1024:
            raise RuntimeError('Unexpected archive size')
        for info in entries:
            name=PurePosixPath(info.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in info.filename or ':' in info.filename:
                raise RuntimeError('Unsafe archive path')
            if ((info.external_attr>>16)&0o170000)==0o120000:
                raise RuntimeError('Archive symlink not allowed')
        if z.testzip() is not None:raise RuntimeError('Corrupt ZIP')
        z.extractall(extraction)
    roots=[p.parent for p in extraction.glob('*/README.md')]
    if len(roots)!=1:raise RuntimeError('Expected one package root')
    package=roots[0]
    if list(package.rglob('LICENSE.candidate')):raise RuntimeError('Candidate license remains')
    if (package/'LICENSE').read_bytes()!=(package/'development-cleanup/LICENSE').read_bytes():
        raise RuntimeError('License mismatch')
    text=(package/'README.md').read_text(encoding='utf-8')
    blocks=[b for b in re.findall(r'```powershell\s*\n(.*?)```',text,re.S) if '$sourceSkill' in b]
    if len(blocks)!=1:raise RuntimeError('README install block not found or ambiguous')
    install=blocks[0]
    checks={'zip_extracts':True,'formal_license_copied':True}
    original_copytree=shutil.copytree

    def copy_using_readme(src,dst,*a,**kw):
        if Path(src).resolve()!=(package/'development-cleanup').resolve():
            return original_copytree(src,dst,*a,**kw)
        destination=Path(dst)
        home=destination.parents[2]
        if destination!=home/'.agents/skills/development-cleanup' or destination.exists():
            raise RuntimeError('Unexpected isolated install destination')
        env=dict(os.environ,USERPROFILE=str(home),HOME=str(home))
        command=['powershell.exe','-NoProfile','-NonInteractive','-Command',install]
        p=subprocess.run(command,cwd=package,env=env,capture_output=True,timeout=30,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if p.returncode:raise RuntimeError('README installer failed')
        expected=snapshot(package/'development-cleanup')
        checks['readme_install_files_match']=snapshot(destination)==expected
        before=snapshot(destination)
        repeat=subprocess.run(command,cwd=package,env=env,capture_output=True,timeout=30,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        checks['existing_install_refused_without_changes']=repeat.returncode!=0 and snapshot(destination)==before
        return dst

    spec=importlib.util.spec_from_file_location('zip_profile_probe',package/'tests/test_new_profile.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.PACKAGE=package
    result_path=work/'profile-result.json'
    previous=os.environ.get('DEVELOPMENT_CLEANUP_PROFILE_RESULT')
    os.environ['DEVELOPMENT_CLEANUP_PROFILE_RESULT']=str(result_path)
    shutil.copytree=copy_using_readme
    try:
        code=module.main()
    finally:
        shutil.copytree=original_copytree
        if previous is None:os.environ.pop('DEVELOPMENT_CLEANUP_PROFILE_RESULT',None)
        else:os.environ['DEVELOPMENT_CLEANUP_PROFILE_RESULT']=previous
    if code or not result_path.exists():raise RuntimeError('Isolated recognition/audit probe failed')
    profile=json.loads(result_path.read_text(encoding='utf-8'))
    checks.update(profile['checks'])
    suite=None
    if args.suite:
        # Keep test repositories independent of the extraction directory depth;
        # Git for Windows may otherwise hit MAX_PATH while creating objects.
        temp=Path(tempfile.mkdtemp(prefix='dcst-'))
        suite_path=work/'suite-result.json'
        env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
        env.update(GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_COUNT='0',
                   TEMP=str(temp),TMP=str(temp),DEVELOPMENT_CLEANUP_TEST_RESULT=str(suite_path))
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(package/'tests/test_cleanup.py')],
                         cwd=package,env=env,capture_output=True,timeout=240)
        (work/'suite-stdout.log').write_bytes(p.stdout)
        (work/'suite-stderr.log').write_bytes(p.stderr)
        if p.returncode or not suite_path.exists():raise RuntimeError('Extracted safety suite failed')
        suite=json.loads(suite_path.read_text(encoding='utf-8'))
        checks['extracted_safety_suite_39_pass']=suite['pass'] and suite['tests_run']==39
    result={'pass':all(checks.values()),'checks':checks,'codex':profile['codex'],
            'model_turn_started':False,'physical_new_account_tested':False,'suite':suite,
            'tested_payload_sha256':snapshot(package/'development-cleanup'),
            'readme_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'installer_sha256':hashlib.sha256(install.encode('utf-8')).hexdigest(),
            'isolation_note':profile['isolation_note']}
    out=os.environ.get('DEVELOPMENT_CLEANUP_ZIP_RESULT')
    if out:Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['pass'] else 1


if __name__=='__main__':sys.exit(main())
