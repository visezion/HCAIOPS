from pathlib import Path

from hcai_ops.agent_deploy.version import compare_versions, increment_version, get_current_agent_version


def test_version_compare():
    assert compare_versions("1.0.0", "1.0.1") == -1
    assert compare_versions("1.0.1", "1.0.0") == 1
    assert compare_versions("1.0.0", "1.0.0") == 0


def test_increment_version():
    assert increment_version(1, 2, 3) == "1.2.3"


def test_get_current_agent_version():
    v = get_current_agent_version()
    assert isinstance(v, str)
