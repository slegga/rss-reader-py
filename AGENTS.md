# AGENTS.md

Guidance for AI agents working on `rss-reader-py`.

This project is a Python rewrite of the Perl `rss-reader`. The following
are **deliberate design choices**. Do not "fix" them without asking.

## Gotchas

- `data/RSS.db` is a part of repo and shall be version controlled.
- Hard exit on errors (raise exceptions, do not swallow).

## Fail-hard error handling
The original used `die` as its primary error strategy. In Python this means:
raise exceptions (often `RuntimeError`) on unexpected conditions. Do **not**
wrap calls in broad `try/except` that swallows errors. Let it crash loudly.

## Scripts in `bin/`
The script `bin/rss-reader.py` uses **uv** and is self-contained. It starts with

```
#!/usr/bin/env -S uv run --quiet --script
```

and declares dependencies in a PEP 723 block. It finds the package itself
(relative to the file), so it needs neither `PYTHONPATH`, activated virtual
environment nor `pip install`.

Never use absolute path to `uv` in the shebang (e.g. `/opt/homebrew/bin/uv`);
`env -S uv` makes the same file work on macOS, Ubuntu and Raspberry Pi OS.
`--quiet` makes uv silent when everything goes well, so that cron only sends
mail on real errors.
