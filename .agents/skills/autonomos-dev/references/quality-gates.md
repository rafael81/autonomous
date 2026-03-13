# Quality Gates

## Required commands

- Fast full suite:
  - `./.venv/bin/python -m pytest -q`
- Golden regression:
  - `./.venv/bin/autonomos run-regression --goldens-dir goldens --suite-path evals/golden_suite.json --report-path .tmp/regression/report.md --json-path .tmp/regression/results.json`
- Parity score:
  - `./.venv/bin/autonomos score-parity`

## When to run what

- CLI output, summaries, memory, or transcript changes:
  - Run pytest.
- Strategy, policy, runtime, recovery, approval, or tool routing changes:
  - Run pytest, regression, and parity score.
- Golden or suite updates:
  - Run regression and parity score after pytest.
- TUI work:
  - Add focused tests for state/render helpers and keep the core pytest suite green.

## Runtime expectations

- Keep `score-parity` at `10.0/10.0` for the current curated suite unless the suite itself is being intentionally revised.
- Do not silently degrade the user-facing parity dashboard:
  - strategy
  - intended golden
  - closest match
  - parity/drift
  - coverage
  - diagnostics / validation hints

## Release expectations

- Update `README.md`, `CHANGELOG.md`, or `docs/` when user-facing commands or workflows change.
- Commit meaningful checkpoints.
- End by running:
  - `git pull --rebase`
  - `bd dolt push`
  - `git push`
- If `bd dolt push` fails, report the exact remote error and continue with the truthful final status.
