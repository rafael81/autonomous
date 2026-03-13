# Release Checklist

## Beta release workflow

1. Confirm version metadata in `pyproject.toml`.
2. Update `README.md` with the current release target and any changed user-facing commands.
3. Add a release entry to `CHANGELOG.md`.
4. Run the test suite:

```bash
./.venv/bin/python -m pytest -q
```

5. Run the documented parity verification loop:

```bash
./.venv/bin/autonomos chat "say hello briefly" --new-session
./.venv/bin/autonomos chat "List the top-level files in this repository and then read the first 20 lines of README.md." --new-session
./.venv/bin/autonomos review --new-session
```

6. Run the golden regression suite:

```bash
./.venv/bin/autonomos run-regression \
  --goldens-dir goldens \
  --suite-path evals/golden_suite.json \
  --report-path .tmp/regression/report.md \
  --json-path .tmp/regression/results.json
```

7. Commit release-prep changes and create a tag if you are releasing from git:

```bash
git tag v0.2.0b0
```

## Blocking items

- A git remote and Dolt remote must exist before the landing-the-plane push steps can succeed.
- `autonomos-2gs` is still open for true approval-artifact capture without bypass mode.
