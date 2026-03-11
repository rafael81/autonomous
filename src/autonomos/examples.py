"""Build the initial example dataset."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from .fixtures import normalize_tui_fixture
from .io import write_jsonl
from .reports import build_report
from .schema import build_event

CODEX_FIXTURE_PATH = Path("/Users/user/project/codex/codex-rs/tui/tests/fixtures/oss-story.jsonl")
CODEX_COMMIT = "a4a9536fd"


def _base_meta(example_id: str, prompt: str, capture_mode: str) -> dict:
    return {
        "example_id": example_id,
        "captured_at": "2026-03-11T00:00:00Z",
        "codex_source": {
            "repo": "/Users/user/project/codex",
            "commit": CODEX_COMMIT,
        },
        "model": "mixed-observation",
        "capture_mode": capture_mode,
        "repro_command": f"autonomos build-examples --output-dir examples  # includes {example_id}",
        "prompt": prompt,
    }


def _simple_session(example_id: str, prompt: str, answer: str, *, with_deltas: bool = True) -> tuple[list[dict], list[dict]]:
    observed = []
    normalized = [
        build_event(ts="2026-03-11T00:00:00Z", source="inferred", channel="meta", event_type="session_start", payload={"example_id": example_id}, raw={"kind": "session_start"}),
        build_event(ts="2026-03-11T00:00:01Z", source="inferred", channel="cli", event_type="user_input", turn_id="turn-1", payload={"text": prompt}, raw={"kind": "user_input"}),
        build_event(ts="2026-03-11T00:00:02Z", source="inferred", channel="cli", event_type="task_started", turn_id="turn-1", payload={}, raw={"kind": "task_started"}),
    ]
    observed.extend(deepcopy(normalized))
    if with_deltas:
        for index, token in enumerate(answer.split(" "), start=3):
            normalized.append(
                build_event(
                    ts=f"2026-03-11T00:00:{index:02d}Z",
                    source="inferred",
                    channel="cli",
                    event_type="assistant_message_delta",
                    turn_id="turn-1",
                    payload={"delta": token if index == 3 else f" {token}"},
                    raw={"kind": "assistant_message_delta"},
                )
            )
    normalized.extend(
        [
            build_event(ts="2026-03-11T00:00:10Z", source="inferred", channel="cli", event_type="assistant_message", turn_id="turn-1", message_id="turn-1", payload={"text": answer}, raw={"kind": "assistant_message"}),
            build_event(ts="2026-03-11T00:00:11Z", source="inferred", channel="cli", event_type="task_complete", turn_id="turn-1", payload={"last_agent_message": answer}, raw={"kind": "task_complete"}),
            build_event(ts="2026-03-11T00:00:12Z", source="inferred", channel="meta", event_type="session_end", turn_id="turn-1", payload={}, raw={"kind": "session_end"}),
        ]
    )
    observed.extend(deepcopy(normalized[3:]))
    return observed, normalized


def _tool_session(example_id: str, prompt: str, *, tool_count: int, failed: bool = False, request_input: bool = False) -> tuple[list[dict], list[dict], str]:
    answer = "I checked the tool outputs and summarized the result."
    observed, normalized = _simple_session(example_id, prompt, answer, with_deltas=False)
    insert_at = 3
    notes = []
    for idx in range(tool_count):
        call_id = f"call-{idx + 1}"
        normalized.insert(
            insert_at,
            build_event(
                ts=f"2026-03-11T00:00:{3 + idx:02d}Z",
                source="inferred",
                channel="tool",
                event_type="tool_call_request",
                turn_id="turn-1",
                call_id=call_id,
                payload={"tool_name": "shell", "arguments": {"command": f"echo step-{idx + 1}"}},
                raw={"kind": "tool_call_request"},
            ),
        )
        normalized.insert(
            insert_at + 1,
            build_event(
                ts=f"2026-03-11T00:00:{4 + idx:02d}Z",
                source="inferred",
                channel="tool",
                event_type="tool_call_result" if not failed or idx < tool_count - 1 else "tool_call_error",
                turn_id="turn-1",
                call_id=call_id,
                payload={"status": "completed" if not failed or idx < tool_count - 1 else "failed", "output": f"step-{idx + 1}"},
                raw={"kind": "tool_call_result"},
            ),
        )
        notes.append(call_id)
        insert_at += 2
    if request_input:
        normalized.insert(
            insert_at,
            build_event(
                ts="2026-03-11T00:00:07Z",
                source="inferred",
                channel="tool",
                event_type="request_user_input",
                turn_id="turn-1",
                call_id="rui-1",
                payload={"questions": 1, "selected_option": "representative"},
                raw={"kind": "request_user_input"},
            ),
        )
    return observed, normalized, ", ".join(notes)


def build_examples_dataset(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    fixture_events = normalize_tui_fixture(CODEX_FIXTURE_PATH)
    fixture_answer = next(event["payload"]["text"] for event in fixture_events if event["event_type"] == "assistant_message")

    scenarios: list[tuple[str, str, list[dict], list[dict], dict, str]] = []

    obs, norm = _simple_session("example-01-simple-short", "Say hello briefly.", "Hello! How can I help you today?")
    scenarios.append(("example-01-simple-short", "Say hello briefly.", obs, norm, _base_meta("example-01-simple-short", "Say hello briefly.", "synthetic"), "Short direct answer."))

    scenarios.append(("example-02-long-stream", "Write a long story.", fixture_events, fixture_events, _base_meta("example-02-long-stream", "Write a long story.", "fixture_capture"), "Uses Codex TUI fixture with real streaming deltas."))

    obs, norm, notes = _tool_session("example-03-single-tool", "Run one tool and summarize.", tool_count=1)
    scenarios.append(("example-03-single-tool", "Run one tool and summarize.", obs, norm, _base_meta("example-03-single-tool", "Run one tool and summarize.", "synthetic"), f"Single tool call: {notes}"))

    obs, norm, notes = _tool_session("example-04-multi-tool", "Run several tools and summarize.", tool_count=2)
    scenarios.append(("example-04-multi-tool", "Run several tools and summarize.", obs, norm, _base_meta("example-04-multi-tool", "Run several tools and summarize.", "synthetic"), f"Multiple tool calls: {notes}"))

    obs, norm, notes = _tool_session("example-05-request-user-input", "Ask me to choose a direction first.", tool_count=1, request_input=True)
    scenarios.append(("example-05-request-user-input", "Ask me to choose a direction first.", obs, norm, _base_meta("example-05-request-user-input", "Ask me to choose a direction first.", "synthetic"), f"Includes request_user_input after {notes}."))

    obs, norm = _simple_session("example-06-plan-only", "Make a plan but do not edit files.", "Plan: inspect, propose steps, and stop before changing files.")
    scenarios.append(("example-06-plan-only", "Make a plan but do not edit files.", obs, norm, _base_meta("example-06-plan-only", "Make a plan but do not edit files.", "synthetic"), "Planning response without mutation."))

    obs, norm, notes = _tool_session("example-07-tool-failure-recovery", "Try a tool that fails, then explain next steps.", tool_count=2, failed=True)
    norm[-3]["payload"]["text"] = "One tool failed, so I explained the failure and suggested a fallback."
    norm[-2]["payload"]["last_agent_message"] = "One tool failed, so I explained the failure and suggested a fallback."
    scenarios.append(("example-07-tool-failure-recovery", "Try a tool that fails, then explain next steps.", obs, norm, _base_meta("example-07-tool-failure-recovery", "Try a tool that fails, then explain next steps.", "synthetic"), f"Includes tool failure across {notes}."))

    obs, norm = _simple_session("example-08-safety-refusal", "Do something unsafe.", "I can't help with unsafe instructions, but I can offer a safer alternative.")
    scenarios.append(("example-08-safety-refusal", "Do something unsafe.", obs, norm, _base_meta("example-08-safety-refusal", "Do something unsafe.", "synthetic"), "Safety refusal structure."))

    obs, norm = _simple_session("example-09-multi-turn-context", "Based on my earlier note, summarize the current state.", "You previously asked for an observation-first CLI, and the current state is a normalized trace plan.")
    scenarios.append(("example-09-multi-turn-context", "Based on my earlier note, summarize the current state.", obs, norm, _base_meta("example-09-multi-turn-context", "Based on my earlier note, summarize the current state.", "synthetic"), "Represents context-carrying answer shape."))

    obs, norm = _simple_session("example-10-session-abort", "Start a task, then stop.", "The session was interrupted before a full answer was completed.", with_deltas=False)
    norm[-2]["event_type"] = "task_complete"
    scenarios.append(("example-10-session-abort", "Start a task, then stop.", obs, norm, _base_meta("example-10-session-abort", "Start a task, then stop.", "synthetic"), "Represents interrupted or early-ended session."))

    for example_id, prompt, observed, normalized, meta, notes in scenarios:
        example_dir = output_dir / example_id
        example_dir.mkdir(parents=True, exist_ok=True)
        (example_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
        write_jsonl(example_dir / "observed.jsonl", observed)
        write_jsonl(example_dir / "normalized.jsonl", normalized)
        (example_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (example_dir / "report.md").write_text(
            build_report(example_id=example_id, prompt=prompt, normalized_events=normalized, notes=notes) + "\n",
            encoding="utf-8",
        )
