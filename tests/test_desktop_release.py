import importlib.util
import json
from pathlib import Path

import pytest

source = Path(__file__).parents[1]/'.github/scripts/publish_desktop.py'
spec = importlib.util.spec_from_file_location('publish_desktop', source)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


@pytest.fixture
def artifacts(tmp_path):
    root = tmp_path/'artifacts'
    version = '0.5.0-beta.17'
    for name, platform, files in [
        ('macOS-ARM64', 'darwin', ['mac-arm64.dmg', 'mac-arm64.zip']),
        ('Windows-X64', 'win32', ['win-x64.exe']),
        ('Linux-X64', 'linux', ['linux-x86_64.AppImage', 'linux-amd64.deb']),
    ]:
        directory = root/('pantheon-desktop-'+name)
        (directory/'desktop').mkdir(parents=True)
        (directory/'desktop-evidence').mkdir()
        (directory/'desktop-evidence/packaged-suites.json').write_text(json.dumps({
            'platform': platform, 'passed': True, 'results': [{'suite': suite, 'passed': True, 'exit_code': 0}
            for suite in ['native-smoke', 'provider-ui-smoke', 'toolbar-ui-smoke', 'system-ui-smoke']]}))
        for name in files:
            (directory/'desktop'/('Pantheon-'+version+'-'+name)).write_bytes(b'x'*(1024*1024+1))
    return root


def test_release_requires_every_platform_and_writes_exact_installer_checksums(artifacts, tmp_path):
    hashes, reports = publisher.prepare_artifacts(artifacts, tmp_path/'output', '0.5.0-beta.17')
    assert len(hashes) == 5 and len(reports) == 3
    assert len((tmp_path/'output/SHA256SUMS.txt').read_text().splitlines()) == 5


def test_a_false_overall_pass_cannot_hide_a_failed_or_missing_packaged_suite(artifacts, tmp_path):
    report = artifacts/'pantheon-desktop-Windows-X64/desktop-evidence/packaged-suites.json'
    value = json.loads(report.read_text())
    value['results'][0]['exit_code'] = 1
    report.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='suites must pass'):
        publisher.prepare_artifacts(artifacts, tmp_path/'output', '0.5.0-beta.17')


def test_mismatched_package_version_never_publishes_another_versions_assets(artifacts, tmp_path):
    with pytest.raises(ValueError, match='Missing or invalid installer'):
        publisher.prepare_artifacts(artifacts, tmp_path/'output', '0.5.0-beta.18')
