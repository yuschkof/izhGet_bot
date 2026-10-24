import pathlib

import pytest

import db.db as db

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """db.py opens 'izhGet.db' by relative path, so every test runs in its own temp dir."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def tmp_db(_isolate_cwd, tmp_path):
    """Чистая izhGet.db во временной папке."""
    db.create_tables()
    return tmp_path


@pytest.fixture
def fixture_html():
    def read(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")
    return read
