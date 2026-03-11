# autonomos

Codex CLI observation toolkit for collecting and normalizing prompt-to-answer traces.

## Goals

- Capture observable Codex CLI session traces.
- Normalize heterogeneous logs into a single JSONL schema.
- Generate reproducible example datasets and concise reports.

## Project layout

- `src/autonomos`: library and CLI
- `tests`: unit tests
- `fixtures`: copied or generated observation fixtures
- `examples`: generated example datasets

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```
