"""Shared test fixtures for rss-reader tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database with the rss-reader schema."""
    dbfile = tmp_path / "test.db"
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    schema_file = migrations_dir / "tabledefs.sql"

    conn = sqlite3.connect(str(dbfile))
    conn.row_factory = sqlite3.Row
    schema = schema_file.read_text()
    conn.executescript(schema)
    conn.close()

    return str(dbfile)
