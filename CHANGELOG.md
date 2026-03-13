# Changelog

## 0.2.0b0 - 2026-03-14

- Made `roma_ws` the default runtime profile for the user-facing chat commands.
- Switched default runtime comparisons to `goldens/` so visible parity output follows real Codex trace references.
- Added intended-golden, closest-match, parity, coverage, drift, and drift-causes fields to runtime output.
- Replaced user-facing synthetic example labels with Codex family or golden references by default.
- Added real Codex family captures and promoted goldens for review, request-user-input, approval, and recovery flows.
- Added a documented parity verification loop and golden regression workflow.
- Tuned structure-inspection behavior toward Codex-like preflight scouting and improved drift scoring for inspection-family runs.
- Compressed drift output so inspection-family mismatches are explained semantically instead of dumping long raw tool sequences.
