"""同步已审核的仓库文件与固定公测包。默认预演，--publish 才提交上传。"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = 'y15208203259-dev/dokou'
TAG = 'v0.1.0-beta.1'
PACKAGE = ROOT / 'dist/渡口-公测版-20261125-群聊交互更新.zip'
ASSET = 'dukou-v0.1.0-beta.1-windows.zip'
GH = shutil.which('gh') or str(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'GitHub CLI/gh.exe')

def run(*args, capture=False):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, encoding='utf-8',
                          stdout=subprocess.PIPE if capture else None).stdout

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--message', default='更新渡口公测版')
    args = parser.parse_args()
    assert run('git', 'remote', 'get-url', 'origin', capture=True).strip() == 'https://github.com/' + REPO + '.git'
    assert run('git', 'branch', '--show-current', capture=True).strip() == 'main'
    run(GH, 'auth', 'status', '--hostname', 'github.com')
    assert PACKAGE.is_file(), '找不到标准公测包'
    with zipfile.ZipFile(PACKAGE) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == 3
        assert {Path(name).name for name in archive.namelist()} == {'渡口.exe', '使用说明.txt', '备份数据.bat'}
    digest = hashlib.sha256(PACKAGE.read_bytes()).hexdigest()
    release = json.loads(run(GH, 'api', f'repos/{REPO}/releases/tags/{TAG}', capture=True))
    print('目标仓库：' + REPO + '；发行版：' + TAG)
    print('安装包 SHA256：' + digest)
    run('git', 'status', '--short', '--untracked-files=normal')
    print('源码仅同步已审核并纳入 Git 的文件；当前不会自动加入应用源码或个人资料。')
    print('现有发行附件：' + ', '.join(asset['name'] for asset in release['assets']))
    if not args.publish:
        print('预演结束，未提交或上传。加 --publish 执行。')
        return
    # 禁止带入别人预先暂存的未知文件。
    allowed = {'README.md', '.gitignore', 'scripts/sync_github.py'}
    staged = run('git', 'diff', '--cached', '--name-only', capture=True).splitlines()
    if set(staged) - allowed:
        raise SystemExit('暂存区含未审核文件，已停止。')
    run('git', 'fetch', 'origin', 'main')
    ahead = run('git', 'rev-list', 'HEAD..origin/main', '--count', capture=True).strip()
    if ahead != '0':
        raise SystemExit('远端有新提交，请先合并；不会强制覆盖。')
    run('git', 'add', '--', *sorted(allowed))
    changed = run('git', 'diff', '--cached', '--name-only', capture=True).strip()
    if changed:
        run('git', '-c', 'user.name=y15208203259-dev', '-c', 'user.email=y15208203259-dev@users.noreply.github.com', 'commit', '-m', args.message)
    run('git', 'push', 'origin', 'main')
    # 临时英文文件名仅用于 GitHub 附件名；本地标准包保持原名。
    with tempfile.TemporaryDirectory(prefix='dukou-release-') as tmp:
        upload = Path(tmp) / ASSET
        shutil.copyfile(PACKAGE, upload)
        run(GH, 'release', 'upload', TAG, str(upload), '--repo', REPO, '--clobber')
    published = json.loads(run(GH, 'api', f'repos/{REPO}/releases/tags/{TAG}', capture=True))
    asset = next(item for item in published['assets'] if item['name'] == ASSET)
    assert asset['size'] == PACKAGE.stat().st_size
    assert asset.get('digest') == 'sha256:' + digest, '远端附件哈希不一致或不可用，请核查'
    print('同步完成：源码已推送，公测包远端大小与SHA256一致。')
    print(asset['browser_download_url'])

if __name__ == '__main__':
    main()
