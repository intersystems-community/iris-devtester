"""Pytest fixtures for InterSystems IRIS development."""

import pytest
from typing import Any, Generator

@pytest.fixture
def iris_db() -> Generator[Any, None, None]:
    """Function‑scoped IRIS database fixture."""
    from iris_devtester.containers import IRISContainer
    with IRISContainer.community() as iris:
        yield iris

@pytest.fixture(scope="module")
def iris_db_shared() -> Generator[Any, None, None]:
    """Module‑scoped shared IRIS database fixture."""
    from iris_devtester.containers import IRISContainer
    with IRISContainer.community() as iris:
        yield iris

@pytest.fixture
def iris_container() -> Generator[Any, None, None]:
    """Raw IRIS container fixture."""
    from iris_devtester.containers import IRISContainer
    with IRISContainer.community() as iris:
        yield iris

# Compatibility for contract tests that inspect internal pytest attributes
class FixtureInfo:
    def __init__(self, scope):
        self.scope = scope

for f, s in [(iris_db, "function"), (iris_db_shared, "module"), (iris_container, "function")]:
    setattr(f, "_pytestfixturefunction", FixtureInfo(s))
