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
- `captures`: saved live capture sessions
- `examples_live`: promoted live sessions in example format

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## Core commands

Generate the baseline dataset:

```bash
./.venv/bin/autonomos build-examples --output-dir examples
```

Print websocket config derived from `OPENAI_API_KEY` or `~/.codex/auth.json`:

```bash
./.venv/bin/autonomos print-ws-config --describe-runtime
```

Run the full observation pipeline:

```bash
./.venv/bin/autonomos observe "say hello briefly" \
  --cwd . \
  --captures-dir captures \
  --promote-dir examples_live \
  --baselines-dir examples
```

Run the user-facing chat flow:

```bash
./.venv/bin/autonomos chat "say hello briefly"
```

The user-facing runtime defaults to `roma_ws`, so `chat`, `resume`, and `repl` use the ChatGPT websocket bridge unless you override `--profile`.

Compare a normalized trace against all baselines:

```bash
./.venv/bin/autonomos compare-baselines captures/session-.../normalized.jsonl --baselines-dir examples
```

## Current state

This repository now provides:

- baseline examples for 10 representative Codex interaction patterns
- fixture and `codex exec --json` normalization
- live capture persistence with prompt/stdout/stderr/raw/normalized/meta outputs
- promotion of live captures into reusable examples
- structural baseline comparison
- a user-facing `chat` command built on the same observation pipeline

The remaining gap to full Codex parity is not the observation harness anymore, but improving the produced interaction behavior so your own CLI matches Codex more closely turn by turn.
