# autonomos

Codex CLI observation toolkit for collecting and normalizing prompt-to-answer traces.

Current release target: `0.2.0b0` (`beta`)

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

The user-facing runtime defaults to `roma_ws`, and `chat`, `resume`, `review`, and `repl`
now compare against `goldens/` by default so the visible score output matches the
real Codex parity axis instead of the older synthetic examples.

Compare a normalized trace against all baselines:

```bash
./.venv/bin/autonomos compare-baselines captures/session-.../normalized.jsonl --baselines-dir examples
```

Show the curated golden regression suite:

```bash
./.venv/bin/autonomos show-eval-suite
```

Run the golden regression suite and write reports:

```bash
./.venv/bin/autonomos run-regression \
  --goldens-dir goldens \
  --suite-path evals/golden_suite.json \
  --report-path .tmp/regression/report.md \
  --json-path .tmp/regression/results.json
```

## Verify parity

Use this short loop to confirm the default runtime is still aligned with the visible
Codex golden families:

```bash
./.venv/bin/autonomos chat "say hello briefly" --new-session
./.venv/bin/autonomos chat "List the top-level files in this repository and then read the first 20 lines of README.md." --new-session
./.venv/bin/autonomos review --new-session
```

For a healthy run, focus on these fields:

- `[strategy]`: the chosen runtime strategy and the Codex family reference it is targeting
- `[parity]`: whether the run exactly matched the intended golden or still drifted from it
- `[coverage]`: how many stored goldens share the observed structure
- `[intended-golden]`: the exact golden prompt family the run is supposed to resemble
- `[closest-match]`: the nearest stored golden after comparison
- `[drift]`: the highest-signal mismatch summary when parity is not exact
- `[drift-causes]`: the structured mismatch categories to tune next

To inspect the full gate used during development:

```bash
./.venv/bin/autonomos show-eval-suite
./.venv/bin/autonomos run-regression \
  --goldens-dir goldens \
  --suite-path evals/golden_suite.json \
  --report-path .tmp/regression/report.md \
  --json-path .tmp/regression/results.json
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

## Beta release notes

`0.2.0b0` is the first beta focused on user-visible Codex parity signals.

- `roma_ws` is the default runtime path for `chat`, `resume`, `review`, and `repl`
- default runtime comparisons now target `goldens/` first instead of the older synthetic examples
- runtime output shows `strategy`, `parity`, `coverage`, `intended-golden`, `closest-match`, `drift`, and `drift-causes`
- real Codex golden coverage now includes structure analysis, review, request-user-input, approval, and recovery families
- the regression workflow is documented and runnable from the CLI

Known limitations:

- exact Codex parity is still approximate for some families, especially approval-gated flows
- `autonomos-2gs` remains open for capturing true approval artifacts without bypass mode
- release/push automation cannot complete until git and dolt remotes are configured
