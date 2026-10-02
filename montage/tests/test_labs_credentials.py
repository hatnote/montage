"""Where labs.py finds the wikireplica credentials (hatnote/montage#621).

In a Toolforge job pod ``~`` is not the tool's home, so the import worker
could not read ~/replica.my.cnf and connected without a password.
"""
import pytest

from montage import labs


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for name in ('TOOL_REPLICA_USER', 'TOOL_REPLICA_PASSWORD', 'TOOL_DATA_DIR'):
        monkeypatch.delenv(name, raising=False)
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    return tmp_path


def test_prefers_tool_replica_env_vars(clean_env, monkeypatch):
    monkeypatch.setenv('TOOL_REPLICA_USER', 'u123')
    monkeypatch.setenv('TOOL_REPLICA_PASSWORD', 'not-a-real-password')
    (clean_env / 'home' / 'replica.my.cnf').write_text('[client]\n')

    assert labs.replica_credentials() == {'user': 'u123',
                                          'password': 'not-a-real-password'}


def test_tool_data_dir_before_home(clean_env, monkeypatch):
    tool_home = clean_env / 'tool'
    tool_home.mkdir()
    (tool_home / 'replica.my.cnf').write_text('[client]\n')
    (clean_env / 'home' / 'replica.my.cnf').write_text('[client]\n')
    monkeypatch.setenv('TOOL_DATA_DIR', str(tool_home))

    assert labs.replica_credentials() == {
        'read_default_file': str(tool_home / 'replica.my.cnf')}


def test_falls_back_to_home(clean_env, monkeypatch):
    monkeypatch.setenv('TOOL_DATA_DIR', str(clean_env / 'missing'))
    (clean_env / 'home' / 'replica.my.cnf').write_text('[client]\n')

    assert labs.replica_credentials() == {
        'read_default_file': str(clean_env / 'home' / 'replica.my.cnf')}


def test_only_one_env_var_is_not_enough(clean_env, monkeypatch):
    monkeypatch.setenv('TOOL_REPLICA_USER', 'u123')
    (clean_env / 'home' / 'replica.my.cnf').write_text('[client]\n')

    assert 'read_default_file' in labs.replica_credentials()


def test_no_credentials_is_a_clear_error(clean_env):
    with pytest.raises(labs.MissingReplicaCredentials):
        labs.replica_credentials()
