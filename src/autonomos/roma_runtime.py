"""Bridge to the roma-cli ChatGPT websocket runtime."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .io import write_jsonl
from .memory import MemoryTurn
from .policy import PromptPolicy
from .schema import build_event
from .strategy import StrategyDecision


DEFAULT_ROMA_ROOT = Path("/Users/user/project/Opus_Aggregator/roma-cli")


@dataclass(frozen=True)
class RomaChatResult:
    final_message: str | None
    session_dir: Path
    normalized_path: Path
    raw_jsonl_path: Path
    stdout_path: Path
    stderr_path: Path
    meta_path: Path


@dataclass(frozen=True)
class RomaAttemptResult:
    result: RomaChatResult
    strategy: StrategyDecision
    comparison_score: int
    comparison_matches: int
    prompt_match_score: int = 10_000
    preferred_match_score: int = 10_000


def run_roma_chat(
    *,
    prompt: str,
    history: list[MemoryTurn],
    captures_dir: Path,
    cwd: Path,
    instructions: str,
    enable_tools: bool,
    policy: PromptPolicy | None = None,
    model: str = "gpt-5.3-codex-spark",
    roma_root: Path = DEFAULT_ROMA_ROOT,
) -> RomaChatResult:
    bridge_script = Path(__file__).resolve().parents[2] / "scripts" / "roma_bridge.mjs"
    payload = {
        "prompt": prompt,
        "history": [{"role": turn.role, "content": turn.text} for turn in history],
        "model": model,
        "instructions": instructions,
        "enableTools": enable_tools,
        "cwd": str(cwd),
        "policy": {
            "promptMode": policy.prompt_mode,
            "toolBudget": policy.tool_budget,
            "maxRepeatedToolCalls": policy.max_repeated_tool_calls,
            "preferredRoots": list(policy.preferred_roots),
            "excludedRoots": list(policy.excluded_roots),
            "stopAfterEvidence": policy.stop_after_evidence,
            "preferredTools": list(policy.preferred_tools),
            "fallbackTool": policy.fallback_tool,
        }
        if policy
        else None,
    }
    completed = subprocess.run(
        ["node", str(bridge_script)],
        cwd=str(cwd),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "PATH": str(roma_root / "node_modules" / ".bin") + ":" + os.environ.get("PATH", ""),
        },
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    session_dir = captures_dir / datetime.now(UTC).strftime("roma-session-%Y%m%dT%H%M%SZ")
    session_dir.mkdir(parents=True, exist_ok=True)
    raw_jsonl_path = session_dir / "raw.jsonl"
    raw_jsonl_path.write_text(completed.stdout if completed.stdout.endswith("\n") else completed.stdout + "\n", encoding="utf-8")
    stdout_path = session_dir / "stdout.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path = session_dir / "stderr.txt"
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    (session_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    normalized_path = session_dir / "normalized.jsonl"
    normalized = normalize_roma_events(prompt=prompt, raw_events=events)
    write_jsonl(normalized_path, normalized)
    meta_path = session_dir / "meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "capture_mode": "roma_ws",
                "runtime": "roma_bridge",
                "returncode": completed.returncode,
                "has_raw_jsonl": True,
                "has_normalized_jsonl": True,
                "cwd": str(cwd),
                "model": model,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    final_message = next(
        (event["payload"].get("text") for event in reversed(normalized) if event["event_type"] == "assistant_message"),
        None,
    )
    return RomaChatResult(
        final_message=final_message,
        session_dir=session_dir,
        normalized_path=normalized_path,
        raw_jsonl_path=raw_jsonl_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        meta_path=meta_path,
    )


def normalize_roma_events(*, prompt: str, raw_events: list[dict]) -> list[dict]:
    normalized: list[dict] = [
        build_event(
            ts="",
            source="live_capture",
            channel="roma_ws",
            event_type="session_start",
            payload={"runtime": "roma_ws"},
            raw={"type": "session_start"},
        ),
        build_event(
            ts="",
            source="inferred",
            channel="user",
            event_type="user_input",
            payload={"text": prompt},
            raw={"text": prompt},
        ),
        build_event(
            ts="",
            source="inferred",
            channel="roma_ws",
            event_type="task_started",
            payload={},
            raw={"type": "task_started"},
        ),
    ]
    for event in raw_events:
        event_type = event.get("type")
        if event_type == "assistant_message_delta":
            normalized.append(
                build_event(
                    ts="",
                    source="live_capture",
                    channel="assistant",
                    event_type="assistant_message_delta",
                    payload={"text": event.get("text", "")},
                    raw=event,
                )
            )
        elif event_type == "assistant_message":
            normalized.append(
                build_event(
                    ts="",
                    source="live_capture",
                    channel="assistant",
                    event_type="assistant_message",
                    payload={"text": event.get("text", "")},
                    raw=event,
                )
            )
        elif event_type == "tool_call":
            normalized.append(
                build_event(
                    ts="",
                    source="live_capture",
                    channel="tool",
                    event_type="tool_call_request",
                    payload={"tool_name": event.get("name"), "args": event.get("args", {})},
                    raw=event,
                    call_id=event.get("callId"),
                )
            )
        elif event_type == "tool_result":
            normalized.append(
                build_event(
                    ts="",
                    source="live_capture",
                    channel="tool",
                    event_type="tool_call_result",
                    payload={"tool_name": event.get("name"), "output": event.get("output")},
                    raw=event,
                    call_id=event.get("callId"),
                )
            )
        elif event_type == "tool_profile":
            normalized.append(
                build_event(
                    ts="",
                    source="live_capture",
                    channel="tool",
                    event_type="tool_profile",
                    payload={
                        "tool_name": event.get("name"),
                        "count": event.get("count"),
                        "summary": event.get("summary", {}),
                    },
                    raw=event,
                )
            )
        elif event_type == "error":
            normalized.append(
                build_event(
                    ts="",
                    source="live_capture",
                    channel="roma_ws",
                    event_type="session_end",
                    payload={"error": event.get("message", "")},
                    raw=event,
                )
            )
        elif event_type == "session_end":
            normalized.append(
                build_event(
                    ts="",
                    source="live_capture",
                    channel="roma_ws",
                    event_type="task_complete",
                    payload={
                        "ok": event.get("ok", False),
                        "tool_summary": event.get("tool_summary", {}),
                        "evidence_count": event.get("evidence_count"),
                        "tool_budget": event.get("tool_budget"),
                    },
                    raw=event,
                )
            )
    normalized.append(
        build_event(
            ts="",
            source="inferred",
            channel="roma_ws",
            event_type="session_end",
            payload={},
            raw={"inferred_from": "roma_bridge_end"},
        )
    )
    return normalized
