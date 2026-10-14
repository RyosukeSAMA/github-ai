from dataclasses import replace

import pytest

from pantheon.core.credentials import CredentialError, CredentialStore
from pantheon.core.pantheon import Pantheon
from pantheon.core.paths import DataPaths


class Vault:
    def __init__(self):
        self.values = {}
        self.fail = False
    def set_password(self, service, name, value):
        if self.fail:
            raise RuntimeError('locked')
        self.values[service, name] = value
    def get_password(self, service, name):
        return self.values.get((service, name))
    def delete_password(self, service, name):
        self.values.pop((service, name), None)


def test_migration_verified_and_locked_vault_preserves_env(tmp_path):
    path = tmp_path / '.env'
    path.write_text('OPENAI_API_KEY=secret-value\nPANTHEON_UI_AUTH_ENABLED=1\n')
    vault = Vault()
    store = CredentialStore(path, backend=vault)
    vault.fail = True
    with pytest.raises(CredentialError, match='preserved'):
        store.migrate()
    assert 'secret-value' in path.read_text()
    vault.fail = False
    assert store.migrate() == ['OPENAI_API_KEY']
    assert 'secret-value' not in path.read_text() + store.references.read_text()
    assert 'PANTHEON_UI_AUTH_ENABLED=1' in path.read_text()
    assert store.get('OPENAI_API_KEY') == 'secret-value'
    vault.values.clear()
    assert store.get('OPENAI_API_KEY') == ''
    assert 'locked' in store.status()['problem']


def test_secure_backend_is_required_and_workspace_scoped(tmp_path, monkeypatch):
    store = CredentialStore(tmp_path / '.env')
    monkeypatch.setattr(store, 'backend', lambda: None)
    with pytest.raises(CredentialError, match='No supported'):
        store.save('OPENAI_API_KEY', 'key', storage='system')
    assert not store.env_path.exists()
    vault = Vault()
    first = CredentialStore(tmp_path / 'first.env', backend=vault)
    other = CredentialStore(tmp_path / 'other.env', backend=vault)
    first.save('OPENAI_API_KEY', 'one', storage='system')
    other.save('OPENAI_API_KEY', 'two', storage='system')
    assert first.get('OPENAI_API_KEY') == 'one'
    assert other.get('OPENAI_API_KEY') == 'two'
    first.save('OPENAI_API_KEY', 'back-to-env', storage='env')
    assert first.get('OPENAI_API_KEY') == 'back-to-env'
    assert first.refs() == []


def test_sdk_resolves_vault_and_never_leaks_env_between_workspaces(tmp_path, monkeypatch):
    config = tmp_path / 'pantheon.yaml'
    config.write_text('pantheon: {hermes: {provider: openai, model: test}}\nllm_providers: {openai: {api_key: "${OPENAI_API_KEY}"}}\n')
    vault = Vault()
    first = tmp_path / 'first.env'
    second = tmp_path / 'second.env'
    CredentialStore(first, backend=vault).save('OPENAI_API_KEY', 'vault-key', storage='system')
    second.write_text('OPENAI_API_KEY=other-key\n')
    monkeypatch.setattr(CredentialStore, 'backend', lambda self: vault)
    monkeypatch.setenv('OPENAI_API_KEY', 'shell-key')
    monkeypatch.setattr(DataPaths, 'for_workspace', lambda: replace(DataPaths(tmp_path, tmp_path, tmp_path / '.pantheon', config, first, True)))
    a = Pantheon(config_path=str(config), env_path=str(first))
    b = Pantheon(config_path=str(config), env_path=str(second))
    assert a.llm_clients['openai'].api_key == 'vault-key'
    assert b.llm_clients['openai'].api_key == 'other-key'
    assert a.services.env_value('OPENAI_API_KEY') == 'vault-key'
