"""SC-006: names removed in feature 036 must not reappear in the package."""

import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "iris_devtester"

DEAD_NAMES = ["HAS_TESTCONTAINERS", "_IRISMockContainer", "_ActualBase", "IRISBase"]


def _sources(root):
    return [p for p in root.rglob("*.py")]


def test_dead_names_absent_from_package():
    offenders = []
    for path in _sources(PACKAGE):
        text = path.read_text(encoding="utf-8")
        for name in DEAD_NAMES:
            if re.search(rf"\b{re.escape(name)}\b", text):
                offenders.append(f"{path.relative_to(PACKAGE)}: {name}")
    assert not offenders, offenders


def test_driver_keyword_absent_from_container_package():
    """``driver=`` was the removed IRISDockerContainer parameter.

    Scoped to ``containers/``: ``IRISConfig(driver=...)`` in other packages is a
    different, live option.
    """
    offenders = []
    for path in _sources(PACKAGE / "containers"):
        if re.search(r"\bdriver\s*=", path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(PACKAGE)))
    assert not offenders, offenders
