"""Tests for CLI (replaces Perl t/rss-reader.t)."""

from __future__ import annotations

import subprocess
import sys

from rss_reader.model import ModelRSS


class TestCLI:
    """Test suite for CLI smoke tests."""

    def test_help(self):
        """CLI --help prints usage and exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "rss_reader", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "rss-reader" in output.lower()

    def test_list_with_local_db(self, temp_db, monkeypatch):
        """CLI --list uses local test DB and shows episodes."""
        m = ModelRSS(dbfile=temp_db)
        m.episodes_update([
            {
                "id": "ep1",
                "title": "Test Episode 1",
                "feed": "TestFeed",
                "description": "A test episode",
                "published_epoch": 1700000100,
                "url": "https://example.com/ep1.mp3",
            },
            {
                "id": "ep2",
                "title": "Test Episode 2",
                "feed": "TestFeed",
                "description": "Another test episode",
                "published_epoch": 1700000200,
                "url": "https://example.com/ep2.mp3",
            },
        ])
        m.states_integer({"retrieve_episodes_epoch": 1700000000})
        m.close()

        monkeypatch.setattr(
            "rss_reader.cli.ModelRSS",
            lambda dryrun=False: ModelRSS(dbfile=temp_db, dryrun=dryrun),
        )

        from rss_reader.cli import main
        exit_code = main(["--list", "2"])
        assert exit_code == 0
