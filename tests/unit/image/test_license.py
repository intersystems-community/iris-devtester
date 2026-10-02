from pathlib import Path

import pytest

from iris_devtester.cli.image.errors import ImageCommandError
from iris_devtester.cli.image.license import LicenseNotice, discover_license_key


def _key(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("KEY")
    return path


def test_option_beats_env_and_cwd(tmp_path):
    opt = _key(tmp_path / "opt" / "a.key")
    env_key = _key(tmp_path / "env" / "b.key")
    _key(tmp_path / "cwd" / "iris.key")
    res = discover_license_key(
        str(opt), env={"IRIS_LICENSE_KEY": str(env_key)}, cwd=tmp_path / "cwd"
    )
    assert res.path == opt.resolve()
    assert res.source == "option"


def test_env_beats_cwd(tmp_path):
    env_key = _key(tmp_path / "env" / "b.key")
    _key(tmp_path / "cwd" / "iris.key")
    res = discover_license_key(None, env={"IRIS_LICENSE_KEY": str(env_key)}, cwd=tmp_path / "cwd")
    assert res.path == env_key.resolve()
    assert res.source == "env"


def test_cwd_iris_key(tmp_path):
    key = _key(tmp_path / "iris.key")
    res = discover_license_key(None, env={}, cwd=tmp_path)
    assert res.path == key.resolve()
    assert res.source == "cwd"
    assert res.notice is None


def test_only_cwd_candidate_is_examined(tmp_path, monkeypatch):
    seen = []
    real_exists, real_is_file = Path.exists, Path.is_file

    def exists(self, *a, **k):
        seen.append(self)
        return real_exists(self, *a, **k)

    def is_file(self, *a, **k):
        seen.append(self)
        return real_is_file(self, *a, **k)

    monkeypatch.setattr(Path, "exists", exists)
    monkeypatch.setattr(Path, "is_file", is_file)
    monkeypatch.setenv("HOME", str(tmp_path))
    _key(tmp_path / "ws" / "iris-devtester" / "iris.key")
    cwd = tmp_path / "work"
    cwd.mkdir()
    seen.clear()
    res = discover_license_key(None, env={}, cwd=cwd)
    assert res.path is None
    assert set(seen) <= {cwd / "iris.key"}
    assert not any("iris-devtester" in str(p) for p in seen)


def test_missing_key_returns_notice_and_continues(tmp_path):
    res = discover_license_key(None, env={}, cwd=tmp_path)
    assert res.path is None
    assert res.source is None
    assert isinstance(res.notice, LicenseNotice)
    assert "--license" in res.notice.message
    assert "IRIS_LICENSE_KEY" in res.notice.message


def test_explicit_missing_option_is_error(tmp_path):
    with pytest.raises(ImageCommandError) as ei:
        discover_license_key(str(tmp_path / "nope.key"), env={}, cwd=tmp_path)
    assert ei.value.exit_code == 2
    assert "nope.key" in ei.value.what
    assert "--license" in ei.value.what or "--license" in ei.value.fix


def test_explicit_missing_env_is_error(tmp_path):
    with pytest.raises(ImageCommandError) as ei:
        discover_license_key(
            None, env={"IRIS_LICENSE_KEY": str(tmp_path / "nope.key")}, cwd=tmp_path
        )
    assert ei.value.exit_code == 2
    assert "IRIS_LICENSE_KEY" in ei.value.what


def test_explicit_directory_is_error(tmp_path):
    with pytest.raises(ImageCommandError):
        discover_license_key(str(tmp_path), env={}, cwd=tmp_path)


def test_describe_reports_path_and_source(tmp_path):
    key = _key(tmp_path / "iris.key")
    res = discover_license_key(None, env={}, cwd=tmp_path)
    text = res.describe()
    assert str(key.resolve()) in text
    assert "iris.key" in text
