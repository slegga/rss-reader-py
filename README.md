# rss-reader-py

Python-omskriving av Perl-verktøyet `rss-reader`. Henter podcast RSS-feeds,
lister de siste uspilte episodene, og lar deg laste ned eller avvise episoder.
Tilstanden lagres i en lokal SQLite-database.

## Funksjoner

- Henter og parser flere podcast-feeds (RSS 2.0 / Atom) parallelt.
- Lister de N siste uavspilte/avviste episodene.
- Markerer episoder som avvist etter ID.
- Laster ned valgte episoder med `wget` til en konfigurerbar katalog.
- Hopper over episoder med uønskede nøkkelord i tittel eller beskrivelse.
- Oppdaterer feed-cachen automatisk maks en gang per 7. dag.
- Støtter `--dryrun` for alle endrende handlinger.

## Avhengigheter

- Python 3.9 eller nyere.
- `uv` (for pakkehåndtering og script-kjøring).
- `wget` på `PATH` (for `--download`-funksjonen).

## Installering

```bash
git clone <repo-url> rss-reader-py
cd rss-reader-py
uv sync
```

## Konfigurasjon

`rss-reader` leser en YAML-konfigurasjonsfil:

```
$CONFIG_DIR/rss-reader.yml
# eller, hvis $CONFIG_DIR ikke er satt:
$HOME/etc/rss-reader.yml
```

Nøkkelen `downloaddir` er påkrevd:

```yaml
downloaddir: /mnt/usb/podcasts
```

## Bruk

```bash
# List de 7 siste uavspilte/avviste episodene (standard).
rss-reader --list

# List 20.
rss-reader --list=20

# Marker to episoder som avvist.
rss-reader --reject=guid1,guid2

# Last ned to episoder til den konfigurerte katalogen.
rss-reader --download=guid3,guid4

# Overstyr nedlastingskatalog for en enkelt kjøring.
rss-reader --download=guid5 --downloaddir=/tmp/dl

# Tving full feed-oppdatering (ignorerer 7-dagers vinduet).
rss-reader --update

# Skriv ut hva som ville skjedd uten å gjøre endringer.
rss-reader --download=guid6 --dryrun
```

Du kan kombinere `--update` med `--list`/`--reject`/`--download`.

## Tilstand

Kjøretidsdata lagres i `data/RSS.db` (en SQLite-database). Skjemaet finnes i
`migrations/tabledefs.sql`:

- `episodes(id, feed, title, description, published_epoch, url, ...)` — én
  rad per hentet episode.
- `states_integer(name, value)` — nøkkel/verdi-par; verktøyet bruker
  `retrieve_episodes_epoch` for å spore siste vellykkede oppdatering.

## Tester

```bash
uv run --with pytest pytest
```

## Prosjektlayout

```
rss-reader-py/
├── bin/
│   └── rss-reader.py           # CLI-script (uv-shebang)
├── rss_reader/
│   ├── __init__.py
│   ├── cli.py                  # CLI-logikk
│   └── model.py                # SQLite-databasemodell
├── tests/
│   ├── conftest.py
│   ├── test_model.py
│   └── test_cli.py
├── migrations/
│   └── tabledefs.sql           # SQLite-skjema
├── data/
│   └── RSS.db                  # SQLite-database (versjonert i repo)
├── pyproject.toml
├── AGENTS.md
├── README.md
└── LICENSE
```

## Lisens

MIT — se `LICENSE`.
