"""Tests for ModelRSS (replaces Perl t/RSS.t)."""

from __future__ import annotations

from rss_reader.model import ModelRSS


class TestModelRSS:
    """Test suite for ModelRSS database operations."""

    def test_read_by_ids_nonexistent(self, temp_db):
        """read_by_ids: nonexistent id returns empty list."""
        m = ModelRSS(dbfile=temp_db)
        assert m.episodes_read_by_ids("nonexistent") == []

    def test_read_by_ids_empty(self, temp_db):
        """read_by_ids: empty input returns empty list."""
        m = ModelRSS(dbfile=temp_db)
        assert m.episodes_read_by_ids() == []

    def test_episodes_update_insert(self, temp_db):
        """episodes_update: insert new record."""
        m = ModelRSS(dbfile=temp_db)
        m.episodes_update([{
            "id": "a",
            "feed": "TestFeed",
            "title": "Episode A",
            "description": "First episode",
            "published_epoch": 1700000000,
            "url": "https://example.com/a.mp3",
        }])
        rows = m.episodes_read_by_ids("a")
        assert len(rows) == 1
        assert rows[0]["title"] == "Episode A"
        assert rows[0]["feed"] == "TestFeed"

    def test_set_downloaded_and_rejected(self, temp_db):
        """set_downloaded and rejected_add work together."""
        m = ModelRSS(dbfile=temp_db)
        # Insert two episodes
        m.episodes_update([
            {"id": "a", "title": "A", "feed": "F", "published_epoch": 100, "url": "http://a.mp3"},
            {"id": "b", "title": "B", "feed": "F", "published_epoch": 200, "url": "http://b.mp3"},
        ])
        m.episodes_set_downloaded("a")
        m.episodes_rejected_add("b")
        handled = m.episodes_read_handeled()
        assert sorted(handled) == ["a", "b"]

    def test_read_all(self, temp_db):
        """read_all returns all rows."""
        m = ModelRSS(dbfile=temp_db)
        m.episodes_update([
            {"id": "a", "title": "A", "feed": "F", "published_epoch": 100, "url": "http://a.mp3"},
            {"id": "b", "title": "B", "feed": "F", "published_epoch": 200, "url": "http://b.mp3"},
        ])
        all_eps = m.episodes_read_all()
        assert len(all_eps) == 2

    def test_states_integer_read_write(self, temp_db):
        """states_integer: write and read back values."""
        m = ModelRSS(dbfile=temp_db)
        m.states_integer({"retrieve_episodes_epoch": 1700000000})
        m.states_integer({"my_custom_key": 42})
        si = m.states_integer()
        assert si["retrieve_episodes_epoch"] == 1700000000
        assert si["my_custom_key"] == 42

    def test_dryrun_defaults_false(self, temp_db):
        """dryrun defaults to False."""
        m = ModelRSS(dbfile=temp_db)
        assert not m.dryrun
