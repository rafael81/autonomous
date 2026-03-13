---
name: autonomos-dev
description: Develop, tune, and validate the Autonomos agent CLI. Use when working inside the `autonomos` repo on runtime orchestration, golden/parity evaluation, Roma websocket integration, CLI commands, regression tooling, or the new Textual TUI. Trigger for code changes, debugging, quality tuning, release prep, and any task that needs project-specific commands, file map, or workflow guardrails.
---

# Autonomos Dev

Use this skill when modifying the Autonomos codebase so project-specific workflow, validation, and runtime conventions stay consistent.

## Quick Start

- Read `AGENTS.md` first and use `bd` for issue tracking before coding.
- Treat `src/autonomos/cli.py`, `src/autonomos/app.py`, `src/autonomos/policy.py`, `src/autonomos/strategy.py`, and `src/autonomos/regression.py` as the main control plane.
- Prefer `goldens/` over `examples/` when reasoning about user-facing runtime parity.
- Run `./.venv/bin/python -m pytest -q` after changes. Use narrower test targets while iterating.
- Use `./.venv/bin/autonomos run-regression --goldens-dir goldens --suite-path evals/golden_suite.json --report-path .tmp/regression/report.md --json-path .tmp/regression/results.json` for parity-sensitive changes.
- Use `./.venv/bin/autonomos score-parity` to confirm the Codex parity score after runtime or orchestration changes.

## Workflow

1. Claim or create the relevant `bd` issue.
2. Inspect the affected control-path files before changing code.
3. Implement the smallest coherent slice.
4. Run targeted checks, then the full pytest suite.
5. If runtime behavior changed, run regression and parity scoring.
6. Commit meaningful checkpoints and push the branch.

## Project Rules

- Runtime chat defaults to `roma_ws`; observation/capture flows still use the Codex-facing capture path.
- Runtime comparison output should be `goldens`-first unless there is a specific reason to use synthetic `examples`.
- Keep agent-loop behavior visible: strategy, parity, diagnostics, and artifacts should remain inspectable from CLI output.
- Prefer built-in repo inspection tools over `bash` when possible.
- Preserve the current approval, request-user-input, resume, and memory flows when refactoring.

## Read These References When Needed

- Read `references/project-map.md` when you need the module map, command map, or where key behaviors live.
- Read `references/quality-gates.md` when you touch runtime orchestration, parity, regressions, releases, or the TUI.

