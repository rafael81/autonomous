# Project Map

## Core control path

- `src/autonomos/cli.py`: user-facing commands, transcript printing, regression entrypoints, parity output.
- `src/autonomos/app.py`: `run_chat`, runtime summary shaping, drift/diagnostic extraction, final message handling.
- `src/autonomos/workflow.py`: observe/capture/promote/compare flow for Codex-facing traces.
- `src/autonomos/strategy.py`: strategy routing, candidate ordering, self-evaluation and family-specific prompt handling.
- `src/autonomos/policy.py`: prompt-mode inference, tool preference hints, recovery/approval/status/review policies.
- `src/autonomos/instructions.py`: base and mode-specific instructions layered on top of strategy/policy.
- `src/autonomos/regression.py`: curated evaluation suite runner, result objects, report/json writers.
- `src/autonomos/scoring.py`: 10-point Codex parity scoring.

## Runtime integrations

- `src/autonomos/roma_runtime.py`: normalizes Roma bridge events into shared trace schema.
- `scripts/roma_bridge.mjs`: ChatGPT websocket bridge, built-in repo tools, recovery-mode behavior.
- `src/autonomos/live_capture.py`: capture persistence for exec-style runs.
- `src/autonomos/exec_normalizer.py`: normalizes raw Codex exec JSONL into the shared schema.

## Trace and evaluation assets

- `goldens/`: real Codex or curated runtime traces used as the primary parity baseline.
- `examples/`: older synthetic baseline examples.
- `evals/golden_suite.json`: main regression suite.
- `codex_traces/`: raw or imported Codex-family traces used to derive goldens.

## Session and UX helpers

- `src/autonomos/memory.py`: session memory persistence, compaction, summaries, listing.
- `src/autonomos/orchestration.py`: approval/request-user-input artifact creation and retry guidance.
- `src/autonomos/compare.py`: structural trace comparison.
- `src/autonomos/delta.py`: human-readable drift summaries.

## Current TUI epic

- Epic: `autonomos-0mm`
- Branch convention now in use: `tui/autonomos-0mm`
- Planned subtasks:
  - `autonomos-7z6`: Textual shell/layout
  - `autonomos-41r`: TUI event store/state model
  - `autonomos-4x5`: interactive composer/commands
  - `autonomos-83y`: adaptive streaming render
  - `autonomos-1tz`: approval + request-user-input + resume
  - `autonomos-nz9`: pager/history/session picker
  - `autonomos-4e5`: polish, theming, snapshots

