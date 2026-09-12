"""SQLite-backed episode store.

Replaces the Perl ``Model::RSS`` module.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ModelRSS:
    """Handle all communication with the SQLite database."""

    def __init__(self, dbfile: str = "data/RSS.db", dryrun: bool = False) -> None:
        self.dbfile = dbfile
        self.dryrun = dryrun
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            dbpath = Path(self.dbfile)
            if not dbpath.is_absolute():
                # Resolve relative to project root (parent of rss_reader/)
                dbpath = Path(__file__).resolve().parent.parent / dbpath
            dbpath.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(dbpath))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute a query and return list of dicts."""
        try:
            cursor = self.conn.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            raise RuntimeError(f"DB ERROR: {e} {self.dbfile}") from e

    def _episode_write(self, data: dict[str, Any]) -> None:
        """Internal write: upsert an episode, merging with existing data."""
        if "id" not in data:
            raise ValueError("Missing id as key")

        old_rows = self._query("SELECT * FROM episodes WHERE id = ?", (data["id"],))
        if old_rows:
            old_row = old_rows[0]
            for key, value in old_row.items():
                if key not in data or data[key] is None or (isinstance(data[key], str) and not data[key]):
                    data[key] = value

        keys = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join("?" for _ in values)
        columns = ", ".join(keys)
        query = f"REPLACE INTO episodes({columns}) VALUES({placeholders})"
        try:
            self.conn.execute(query, values)
            self.conn.commit()
        except Exception as e:
            raise RuntimeError(f"DB ERROR: {e} {self.dbfile} {json.dumps(data)}") from e

    def episodes_update(self, hashes: list[dict[str, Any]]) -> None:
        """Update episodes with given list of hashes."""
        for h in hashes:
            if "id" in h:
                old_rows = self.episodes_read_by_ids(h["id"])
                if old_rows:
                    old_hash = dict(old_rows[0])
                    old_hash.update(h)
                    h = old_hash
            keys = list(h.keys())
            values = list(h.values())
            placeholders = ", ".join("?" for _ in values)
            columns = ", ".join(keys)
            query = f"REPLACE INTO episodes({columns}) VALUES({placeholders})"
            try:
                self.conn.execute(query, values)
                self.conn.commit()
            except Exception as e:
                raise RuntimeError(f"DB ERROR: {e} {self.dbfile} {json.dumps(h)}") from e

    def episodes_rejected_add(self, *ids: str) -> None:
        """Mark episodes as rejected."""
        for episode_id in ids:
            self._episode_write({"id": episode_id, "is_rejected": 1})

    def episodes_read_handeled(self) -> list[str]:
        """Return IDs of all rejected or downloaded episodes."""
        rows = self._query("SELECT id FROM episodes WHERE is_rejected = 1 OR is_downloaded = 1")
        return [row["id"] for row in rows]

    def episodes_read_all(self) -> list[dict[str, Any]]:
        """Return all episodes."""
        return self._query("SELECT * FROM episodes")

    def episodes_read_by_ids(self, *ids: str) -> list[dict[str, Any]]:
        """Get episodes by IDs."""
        if not ids:
            return []
        placeholders = ", ".join("?" for _ in ids)
        return self._query(f"SELECT * FROM episodes WHERE id IN ({placeholders})", ids)

    def episodes_set_downloaded(self, *ids: str) -> None:
        """Mark episodes as downloaded."""
        for episode_id in ids:
            self._episode_write({"id": episode_id, "is_downloaded": 1})

    def states_integer(self, data: dict[str, int] | None = None) -> dict[str, int]:
        """Read or write key-value pairs in states_integer table."""
        if data is not None:
            for name, value in data.items():
                query = "REPLACE INTO states_integer(name, value) VALUES(?, ?)"
                try:
                    self.conn.execute(query, (name, value))
                    self.conn.commit()
                except Exception as e:
                    raise RuntimeError(f"DB ERROR: {e} {self.dbfile} {json.dumps(data)}") from e

        rows = self._query("SELECT name, value FROM states_integer")
        return {row["name"]: row["value"] for row in rows}
