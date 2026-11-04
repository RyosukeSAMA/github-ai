"""Publish an existing beta draft from a successful, tree-matching native CI run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def gh_json(*args):
    return json.loads(command('gh', *args))


def file_hash(file):
    hasher = hashlib.sha256()
    with file.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def prepare_artifacts(root, output, version, required_suites=None):
    expected = {
        'pantheon-desktop-macOS-ARM64': ('darwin', [f'Pantheon-{version}-mac-arm64.dmg', f'Pantheon-{version}-mac-arm64.zip']),
        'pantheon-desktop-Windows-X64': ('win32', [f'Pantheon-{version}-win-x64.exe']),
        'pantheon-desktop-Linux-X64': ('linux', [f'Pantheon-{version}-linux-x86_64.AppImage', f'Pantheon-{version}-linux-amd64.deb']),
    }
    required = required_suites or {'native-smoke', 'provider-ui-smoke', 'toolbar-ui-smoke', 'system-ui-smoke'}
    reports = {}
    output.mkdir(parents=True, exist_ok=True)
    for platform_name, (platform, assets) in expected.items():
        report = json.loads((root/platform_name/'desktop-evidence/packaged-suites.json').read_text())
        stages = report.get('results', [])
        if (report.get('platform') != platform or report.get('passed') is not True
                or not required.issubset({stage['suite'] for stage in stages})
                or any(stage.get('passed') is not True or stage.get('exit_code') != 0 for stage in stages)):
            raise ValueError(f'{platform_name}: all required actual packaged suites must pass')
        reports[platform_name] = report
        for name in assets:
            source = root / platform_name / 'desktop' / name
            if not source.is_file() or source.is_symlink() or not 1024*1024 < source.stat().st_size < 1200*1024*1024:
                raise ValueError('Missing or invalid installer: '+name)
            shutil.copy2(source, output/name)
    hashes = {}
    for file in sorted(output.glob('Pantheon-*')):
        hashes[file.name] = file_hash(file)
    if len(hashes) != 5:
        raise ValueError('The release requires exactly five native installer assets')
    (output/'SHA256SUMS.txt').write_text(''.join(value+'  '+name+'\n' for name, value in hashes.items()))
    return hashes, reports


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'\d{1,15}', args.run_id) or not re.fullmatch(r'[a-f0-9]{40}', args.target) or not re.fullmatch(r'v\d+\.\d+\.\d+-beta\.\d+', args.tag):
        raise ValueError('Use a numeric CI run, full source commit and beta tag')
    repo = os.environ['GITHUB_REPOSITORY']
    if repo != 'RyosukeSAMA/github-ai':
        raise ValueError('Publishing is restricted to the official repository')
    run = gh_json('api', f'repos/{repo}/actions/runs/{args.run_id}')
    if (run['status'] != 'completed' or run['conclusion'] != 'success'
            or run.get('path') != '.github/workflows/desktop.yml'
            or run.get('head_repository', {}).get('full_name') != repo):
        raise ValueError('Choose a successful official Desktop beta run')
    tested = run['head_sha']
    tested_tree = gh_json('api', f'repos/{repo}/git/commits/{tested}')['tree']['sha']
    target_tree = gh_json('api', f'repos/{repo}/git/commits/{args.target}')['tree']['sha']
    if tested_tree != target_tree:
        raise ValueError('Release source differs from the tested source tree')
    version = json.loads(command('git', 'show', args.target+':desktop/package.json'))['version']
    if args.tag != 'v'+version:
        raise ValueError('Release tag differs from the tested package version')
    release = gh_json('release', 'view', args.tag, '--repo', repo, '--json', 'databaseId,isDraft,targetCommitish')
    if release['isDraft'] is not True or release['targetCommitish'] != args.target:
        raise ValueError('Prepare an unpublished draft targeting the exact reviewed commit first')
    root = Path('release-artifacts')
    output = Path('release-upload')
    if root.exists() or output.exists():
        raise ValueError('Use a fresh release job directory')
    subprocess.run(['gh', 'run', 'download', args.run_id, '--repo', repo, '--dir', str(root)], check=True)
    suite_source = command('git', 'show', args.target+':desktop/test/packaged-suites.cjs')
    required_suites = set(re.findall(r"\['([a-z-]+smoke)',\s*\d+\]", suite_source))
    if not {'native-smoke', 'provider-ui-smoke', 'toolbar-ui-smoke', 'system-ui-smoke'}.issubset(required_suites):
        raise ValueError('Could not validate every required suite from the tested source')
    hashes, reports = prepare_artifacts(root, output, version, required_suites)
    (output/f'verification-beta.{version.rsplit(".", 1)[-1]}.json').write_text(json.dumps({
        'version': version, 'validated_ci_commit': tested, 'merged_commit': args.target,
        'ci_run': int(args.run_id), 'platforms': reports, 'sha256': hashes,
        'paid_api_calls': 0, 'real_os_installation_tested': False, 'signing_notarization': 'excluded'}, indent=2))
    files = sorted(output.iterdir())
    subprocess.run(['gh', 'release', 'upload', args.tag, '--repo', repo, '--clobber', *map(str, files)], check=True)
    uploaded = gh_json('api', f'repos/{repo}/releases/{release["databaseId"]}')
    assets = {item['name']: item for item in uploaded['assets']}
    for file in files:
        expected = file_hash(file)
        asset = assets.get(file.name)
        if not asset or asset['size'] != file.stat().st_size:
            raise ValueError('Uploaded asset size mismatch: '+file.name)
        if asset.get('digest'):
            if asset['digest'] != 'sha256:'+expected:
                raise ValueError('Uploaded SHA-256 mismatch: '+file.name)
        else:
            verify = Path('release-verify')
            subprocess.run(['gh', 'release', 'download', args.tag, '--repo', repo, '--pattern', file.name, '--dir', str(verify)], check=True)
            if file_hash(verify/file.name) != expected:
                raise ValueError('Downloaded verification mismatch: '+file.name)
    subprocess.run(['gh', 'release', 'edit', args.tag, '--repo', repo, '--draft=false', '--prerelease', '--latest=false'], check=True)
    print('Published verified Desktop beta: https://github.com/'+repo+'/releases/tag/'+args.tag)


if __name__ == '__main__':
    main()
