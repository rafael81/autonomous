# Codex Trace Tuning Workflow

This project tunes Autonomos against real Codex behavior by capturing live Codex traces, curating them into goldens, and comparing runtime output against those goldens.

## 1. Inspect the configured prompt families

```bash
./.venv/bin/autonomos show-core-families
```

These families are the reproducible prompts used to gather canonical Codex traces.
The configured set now includes stable chat families plus review, request-user-input,
approval, and recovery-oriented prompts so new Codex captures can be promoted
through the same workflow.

## 2. Capture a real Codex trace

```bash
./.venv/bin/autonomos capture-codex-family codex-readme-inspection --promote-to-golden
```

This writes a canonical capture under `codex_traces/<family_id>/` with:

- `prompt.txt`
- `stdout.txt`
- `stderr.txt`
- `raw.jsonl`
- `normalized.jsonl`
- `meta.json`

If `--promote-to-golden` is used, the normalized trace is also imported into `goldens/<family_id>/`.

## 3. Analyze drift against a golden

```bash
./.venv/bin/autonomos analyze-drift goldens/codex-readme-inspection/normalized.jsonl captures/.../normalized.jsonl
```

The drift output is grouped into actionable categories:

- strategy selection
- preamble shape
- tool routing
- tool count
- result shape
- retry behavior
- user-input artifacts
- final answer formatting

## 4. Run regression gating

```bash
./.venv/bin/autonomos run-regression --goldens-dir goldens --suite-path evals/golden_suite.json
```

Regression reports now include both structural score and structured drift causes so tuning can focus on the biggest gaps first.
