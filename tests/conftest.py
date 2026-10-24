import pathlib

import pytest

import db.db as db

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Чистая izhGet.db во временной папке (db.py открывает файл по относительному пути)."""
    monkeypatch.chdir(tmp_path)
    db.create_tables()
    return tmp_path


@pytest.fixture
def fixture_html():
    def read(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")
    return read
