"""Shared state helpers for the Textual TUI."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .app import ChatRunSummary
from .io import read_jsonl
from .memory import list_sessions, load_session_memory, render_memory_context


@dataclass
class PendingApproval:
    request_path: Path
    question: str
    options: list[dict]


@dataclass
class PendingUserInput:
    request_path: Path
    question: str
    options: list[dict]


@dataclass
class TuiSessionState:
    session_id: str
    memory_dir: Path
    transcript_lines: list[str] = field(default_factory=list)
    diagnostics_lines: list[str] = field(default_factory=list)
    parity_lines: list[str] = field(default_factory=list)
    status_lines: list[str] = field(default_factory=list)
    pending_approval: PendingApproval | None = None
    pending_user_input: PendingUserInput | None = None
    last_summary: ChatRunSummary | None = None

    def add_local_status(self, text: str) -> None:
        self.status_lines.append(text)

    def add_user_prompt(self, prompt: str) -> None:
        self.transcript_lines.append(f"user> {prompt}")

    def apply_summary(self, summary: ChatRunSummary) -> None:
        self.last_summary = summary
        for line in build_transcript_lines(summary.normalized_path):
            if self.transcript_lines and self.transcript_lines[-1] == line:
                continue
            self.transcript_lines.append(line)
        self.parity_lines = build_parity_lines(summary)
        self.diagnostics_lines = build_diagnostic_lines(summary)
        self.pending_approval = load_pending_approval(summary.approval_request_path)
        self.pending_user_input = load_pending_user_input(summary.request_user_input_path)

    def context_text(self) -> str:
        turns = load_session_memory(self.memory_dir, self.session_id)
        return render_memory_context(turns) or "No stored context."

    def session_rows(self) -> list[tuple[str, int, str | None]]:
        return list_sessions(self.memory_dir)


def build_transcript_lines(normalized_path: Path | None) -> list[str]:
    if normalized_path is None or not normalized_path.exists():
        return ["status> missing normalized trace"]
    rows = read_jsonl(normalized_path)
    lines: list[str] = []
    pending_delta: str | None = None
    final_message: str | None = None
    for row in rows:
        event_type = row.get("event_type")
        payload = row.get("payload", {})
        if event_type == "assistant_message_delta":
            pending_delta = payload.get("text", "")
            continue
        if event_type == "status_update":
            lines.append(f"status> {payload.get('text', '')}")
            continue
        if event_type == "user_input":
            lines.append(f"user> {payload.get('text', '')}")
            continue
        if event_type == "assistant_message":
            if pending_delta and pending_delta != payload.get("text", ""):
                lines.append(f"assistant~ {pending_delta}")
            text = payload.get("text", "")
            lines.append(f"assistant> {text}")
            final_message = text
            pending_delta = None
            continue
        if event_type == "tool_call_request":
            tool_name = payload.get("tool_name", "tool")
            args = payload.get("args", {})
            lines.append(f"tool> request {tool_name} {args}")
            continue
        if event_type == "tool_call_result":
            tool_name = payload.get("tool_name", "tool")
            output = str(payload.get("output", "")).splitlines()[0] if payload.get("output") else ""
            lines.append(f"tool> result {tool_name} {output}")
            continue
    if final_message:
        lines.append(f"final> {final_message}")
    return lines or ["status> no transcript rows"]


def build_parity_lines(summary: ChatRunSummary) -> list[str]:
    lines = [
        f"strategy: {summary.strategy_id}",
        f"reference: {summary.intended_match_example_id or summary.closest_match_example_id or summary.baseline_example_id}",
        f"coverage: {summary.baseline_matches}/{summary.baseline_total}",
    ]
    if summary.intended_match_example_id is not None:
        if summary.intended_match_score == 0:
            lines.append(f"parity: exact match for {summary.intended_match_example_id}")
        else:
            lines.append(f"parity: drift from {summary.intended_match_example_id} (score={summary.intended_match_score})")
    elif summary.closest_match_example_id is not None:
        lines.append(f"parity: closest golden is {summary.closest_match_example_id} (score={summary.closest_match_score})")
    if summary.drift_summary:
        lines.append(f"drift: {summary.drift_summary}")
    elif summary.intended_match_example_id and summary.intended_match_score == 0:
        lines.append("drift: aligned")
    return lines


def build_diagnostic_lines(summary: ChatRunSummary) -> list[str]:
    lines = [f"policy: {summary.orchestration_summary}", f"session: {summary.session_dir}"]
    lines.append(f"normalized: {summary.normalized_path}" if summary.normalized_path else "normalized: none")
    if summary.request_user_input_path:
        lines.append(f"request-user-input: {summary.request_user_input_path}")
    if summary.approval_request_path:
        lines.append(f"approval: {summary.approval_request_path}")
    for hint in summary.validation_hints:
        lines.append(f"validation: {hint}")
    for item in summary.runtime_diagnostics:
        lines.append(f"runtime: {item}")
    return lines


def load_pending_approval(path: Path | None) -> PendingApproval | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PendingApproval(
        request_path=path,
        question=payload.get("question", "Approve?"),
        options=payload.get("options", []),
    )


def load_pending_user_input(path: Path | None) -> PendingUserInput | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    questions = payload.get("questions", [])
    question = questions[0] if questions else {}
    return PendingUserInput(
        request_path=path,
        question=question.get("question", "Choose an option."),
        options=question.get("options", []),
    )
