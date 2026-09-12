"""Command-line entry point.

Replaces the Perl ``bin/rss-reader.pl`` script.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import formatdate, parsedate_to_datetime
from pathlib import Path
from typing import Any

import feedparser
import yaml

from .model import ModelRSS

FEEDS = [
    "http://vettogvitenskap.libsyn.com/rss",
    "https://rss.podplaystudio.com/608.xml",
    "https://feeds.acast.com/public/shows/30-minutter-inn-i-fremtiden",
    "https://sindrel.github.io/nrk-pod-feeds/rss/abels_taarn.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/burde_vaert_pensum.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/ekko_-_et_aktuelt_samfunnsprogram.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/kjente_boeker_paa_4_minutter.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/oppdatert.xml",
    "https://sindrel.github.io/nrk-pod-feeds/rss/trygdekontoret.xml",
    "https://feed.podbean.com/vertshuset/feed.xml",
    "https://media.rss.com/spacepodden/feed.xml",
]

UNWANTED = ["antipanel", "reprise", "trær", "plante"]


def _load_config() -> dict[str, Any]:
    """Load YAML config from $CONFIG_DIR/rss-reader.yml or $HOME/etc/rss-reader.yml."""
    config_dir = os.environ.get("CONFIG_DIR", os.path.join(os.path.expanduser("~"), "etc"))
    config_file = os.path.join(config_dir, "rss-reader.yml")
    if not os.path.exists(config_file):
        raise SystemExit(f"Config file not found: {config_file}")
    with open(config_file) as f:
        return yaml.safe_load(f) or {}


def _get_downloaddir(args_downloaddir: str | None, config: dict[str, Any]) -> str:
    """Get download directory from args or config."""
    if args_downloaddir:
        return args_downloaddir
    downloaddir = config.get("downloaddir")
    if downloaddir:
        print(f"downloaddir: {downloaddir}")
        return downloaddir
    config_dir = os.environ.get("CONFIG_DIR", os.path.join(os.path.expanduser("~"), "etc"))
    config_file = os.path.join(config_dir, "rss-reader.yml")
    raise SystemExit(f"Missing config downloaddir: in file {config_file}")


def _fetch_feed(url: str) -> feedparser.FeedParserDict | None:
    """Fetch and parse a single RSS feed."""
    try:
        print(url)
        return feedparser.parse(url)
    except (OSError, ValueError) as e:
        warn(f"Failed to fetch {url}: {e}")
        return None


def _parse_feed_items(
    feed: feedparser.FeedParserDict,
    handled_ids: set[str],
    retrieve_epoch: int,
    nore: int,
) -> list[dict[str, Any]]:
    """Parse feed entries and return valid episode items."""
    items: list[dict[str, Any]] = []
    feed_title = feed.get("feed", {}).get("title", "Unknown")

    for entry in feed.entries[:nore]:
        if not entry:
            continue

        # Get published date
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            published_epoch = int(time.mktime(published))
        else:
            # Try pubDate from raw XML
            pub_date_str = entry.get("published") or entry.get("updated", "")
            if pub_date_str:
                try:
                    dt = parsedate_to_datetime(pub_date_str)
                    published_epoch = int(dt.timestamp())
                except (ValueError, TypeError):
                    warn("Missing published date for entry")
                    continue
            else:
                warn("Missing published")
                continue

        # Skip if older than retrieve epoch
        if retrieve_epoch and retrieve_epoch > published_epoch:
            continue

        title = entry.get("title", "")
        # Filter unwanted keywords
        if any(kw in title.lower() for kw in UNWANTED):
            continue

        description = entry.get("summary", entry.get("description", ""))
        if any(kw in description.lower() for kw in UNWANTED):
            continue

        # Get URL (enclosure or link)
        url = None
        enclosures = entry.get("enclosures", [])
        if enclosures:
            url = enclosures[0].get("href") or enclosures[0].get("url")
        if not url:
            url = entry.get("link")
        if not url:
            continue
        if "mp3" not in url.lower():
            continue

        episode_id = entry.get("id") or entry.get("link", "")
        if not episode_id:
            continue

        if episode_id in handled_ids:
            continue

        # Clean URL (remove wget prefix and query string)
        url = url.replace('wget ', '').split('?')[0]

        items.append({
            "id": episode_id,
            "feed": feed_title,
            "title": title,
            "description": description,
            "url": url,
            "published_epoch": published_epoch,
        })

    return items


def _get_new_episodes(model: ModelRSS, update: bool = False) -> list[dict[str, Any]]:
    """Fetch new episodes from all feeds and update the database."""
    print("Update the database")
    states = model.states_integer()
    retrieve_epoch = states.get("retrieve_episodes_epoch", 1000)

    if update:
        retrieve_epoch = int(time.time()) - 4 * 30 * 24 * 60 * 60

    handled_ids = set(model.episodes_read_handeled())
    nore = 300

    # Fetch feeds in parallel
    all_items: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_fetch_feed, url): url for url in FEEDS}
        for future in as_completed(futures):
            feed = future.result()
            if feed is None:
                continue
            items = _parse_feed_items(feed, handled_ids, retrieve_epoch, nore)
            all_items.extend(items)

    # Update database
    model.episodes_update(all_items)
    model.states_integer({"retrieve_episodes_epoch": int(time.time())})
    return all_items


def warn(msg: str) -> None:
    """Print a warning to stderr."""
    print(msg, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for rss-reader CLI."""
    parser = argparse.ArgumentParser(
        prog="rss-reader",
        description="RSS Reader. Pick episodes to download.",
    )
    parser.add_argument(
        "--list",
        type=int,
        default=0,
        metavar="N",
        help="List the N best episodes (default: 7)",
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Print to screen instead of doing changes",
    )
    parser.add_argument(
        "--reject",
        type=str,
        help="Comma separated list of episode ids to reject",
    )
    parser.add_argument(
        "--download",
        type=str,
        help="Comma separated list of episode ids to download",
    )
    parser.add_argument(
        "--downloaddir",
        type=str,
        help="Dir to download to",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Force full update of database based on feeds",
    )

    args = parser.parse_args(argv)

    model = ModelRSS(dryrun=args.dryrun)

    list_count = args.list if args.list else 7

    if args.update:
        list_count = 300

    # Determine if we need to fetch new episodes
    states = model.states_integer()
    retrieve_epoch = states.get("retrieve_episodes_epoch", 0)
    now = int(time.time())

    if args.update or retrieve_epoch < now - 7 * 24 * 60 * 60:
        _get_new_episodes(model, update=args.update)

    # Handle --reject
    if args.reject:
        rejected = [x.strip() for x in args.reject.split(",")]
        model.episodes_rejected_add(*rejected)
        return 0

    # Handle --download
    if args.download:
        config = _load_config()
        downloaded = [x.strip() for x in args.download.split(",")]
        episodes = model.episodes_read_by_ids(*downloaded)
        downloaddir = _get_downloaddir(args.downloaddir, config)

        urls = []
        for ep in episodes:
            u = ep["url"].replace("wget ", "").split("?")[0]
            urls.append(u)

        if args.dryrun:
            print(f"DRYRUN: wget -P {downloaddir} {' '.join(urls)}")
        else:
            result = subprocess.run(["wget", "-P", downloaddir] + urls, check=False)
            if result.returncode != 0:
                print(f"wget failed: exit={result.returncode} {' '.join(urls)}", file=sys.stderr)
                return 1
            for ep in episodes:
                model.episodes_set_downloaded(ep["id"])

        # Rename duplicates
        dl_path = Path(downloaddir)
        if dl_path.exists():
            for f in dl_path.iterdir():
                if f.is_file():
                    stat = f.stat()
                    if stat.st_size == 0:
                        print(f"File size for {f} is 0. Media is probably full.", file=sys.stderr)
                        return 1
                    name = f.name
                    m = re.match(r"^(.+)\.mp3\.(\d+)$", name, re.IGNORECASE)
                    if m:
                        newname = f"{m.group(1)}.{m.group(2)}.mp3"
                        target = dl_path / newname
                        if target.exists():
                            newname = f"{m.group(1)}.{m.group(2)}.{random.randint(0, 99999)}.mp3"
                        print(f"rename {name} to {newname}")
                        f.rename(dl_path / newname)

        return 0

    # Handle --list
    if args.list or not any([args.reject, args.download, args.update]):
        episodes = model.episodes_read_all()
        # Filter and sort
        filtered = [
            ep for ep in episodes
            if ep.get("title") and not ep.get("is_rejected") and not ep.get("is_downloaded")
        ]
        filtered.sort(key=lambda x: x.get("published_epoch", 0), reverse=True)

        for item in filtered[:list_count]:
            if not item.get("published_epoch"):
                continue
            date_str = formatdate(item["published_epoch"], usegmt=True)
            print(f"{item['id']} {date_str} {item['feed']}")
            for key in ("title", "description", "url"):
                print(item.get(key, ""))
            print("--")
        return 0

    print("Must use options to do something", file=sys.stderr)
    return 1
