"""Allow running rss_reader as a module: python -m rss_reader"""
from rss_reader.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
