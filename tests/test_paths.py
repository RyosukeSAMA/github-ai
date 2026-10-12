from pantheon.core.paths import DataPaths


def test_new_workspaces_share_config_but_isolate_project_data(tmp_path, monkeypatch):
    monkeypatch.delenv('PANTHEON_STATE_MODE')
    monkeypatch.setenv('PANTHEON_DATA_DIR', str(tmp_path / 'app-data'))
    a = DataPaths.for_workspace(tmp_path / 'a')
    b = DataPaths.for_workspace(tmp_path / 'b')
    assert a.config == b.config
    assert a.env == b.env
    assert a.state != b.state
    assert DataPaths.for_workspace(tmp_path / 'a' / '..' / 'a') == a


def test_existing_workspace_keeps_its_data_and_config(tmp_path, monkeypatch):
    monkeypatch.delenv('PANTHEON_STATE_MODE')
    (tmp_path / '.pantheon').mkdir()
    paths = DataPaths.for_workspace(tmp_path)
    assert paths.legacy
    assert paths.state == tmp_path / '.pantheon'
    assert paths.config == tmp_path / 'config' / 'pantheon.yaml'


def test_explicit_config_path_is_resolved_against_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv('PANTHEON_CONFIG', 'custom.yaml')
    assert DataPaths.for_workspace(tmp_path).config == tmp_path / 'custom.yaml'
