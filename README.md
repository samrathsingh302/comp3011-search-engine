# COMP3011 Search Engine

A Python search engine that crawls [quotes.toscrape.com](https://quotes.toscrape.com), builds an inverted index of word occurrences with positional information, and serves ranked queries through an interactive shell.

University of Leeds, COMP3011 Web Services and Web Data, Coursework 2 (2025-26).

## Status

Scaffold only. The crawler, indexer, search engine, and CLI are built incrementally across the sessions logged in `docs/decisions.md`.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

## Usage

```powershell
python -m src.main
```

Then inside the shell: `build`, `load`, `print <word>`, `find <query>`, `stats`, `exit`.

## Testing

```powershell
pytest
```

Coverage gate is 85% (set in `pytest.ini`); the target is 90 percent or higher.

## Design notes

See [`docs/decisions.md`](docs/decisions.md) for a running log of design choices and [`GENAI_EVALUATION.md`](GENAI_EVALUATION.md) for the GenAI usage reflection.

## License

MIT, see [`LICENSE`](LICENSE).
