from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from tests.fixtures.build_fixtures import build
from tests.fixtures.spec import AS_OF

AS_OF_DATE = date.fromisoformat(AS_OF)


@pytest.fixture(scope="session")
def department(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dest = Path(__file__).parent / "fixtures" / "department"
    return build(dest)


@pytest.fixture(scope="session")
def as_of() -> date:
    return AS_OF_DATE
