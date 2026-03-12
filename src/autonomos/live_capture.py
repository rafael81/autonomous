"""Live process capture helpers."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .exec_normalizer import normalize_exec_events
from .io import read_jsonl, write_jsonl


@dataclass
class LiveCaptureResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass
class SavedCapturePaths:
    session_dir: Path
    prompt_path: Path
    raw_stdout_path: Path
    raw_stderr_path: Path
    raw_jsonl_path: Path | None
    normalized_path: Path | None
    meta_path: Path


def run_capture(command: list[str], *, cwd: Path | None = None) -> LiveCaptureResult:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    return LiveCaptureResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def save_capture_session(
    *,
    result: LiveCaptureResult,
    prompt: str,
    output_root: Path,
    capture_mode: str = "live_capture",
) -> SavedCapturePaths:
    session_id = datetime.now(UTC).strftime("session-%Y%m%dT%H%M%SZ")
    session_dir = output_root / session_id
    return save_capture_snapshot(
        result=result,
        prompt=prompt,
        output_dir=session_dir,
        capture_mode=capture_mode,
    )


def save_capture_snapshot(
    *,
    result: LiveCaptureResult,
    prompt: str,
    output_dir: Path,
    capture_mode: str = "live_capture",
    metadata: dict | None = None,
) -> SavedCapturePaths:
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = output_dir / "prompt.txt"
    raw_stdout_path = output_dir / "stdout.txt"
    raw_stderr_path = output_dir / "stderr.txt"
    raw_jsonl_path: Path | None = None
    normalized_path: Path | None = None
    meta_path = output_dir / "meta.json"

    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    raw_stdout_path.write_text(result.stdout, encoding="utf-8")
    raw_stderr_path.write_text(result.stderr, encoding="utf-8")

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if lines and all(_looks_like_json(line) for line in lines):
        raw_jsonl_path = output_dir / "raw.jsonl"
        raw_jsonl_path.write_text(result.stdout if result.stdout.endswith("\n") else result.stdout + "\n", encoding="utf-8")
        normalized = normalize_exec_events(read_jsonl(raw_jsonl_path))
        normalized_path = output_dir / "normalized.jsonl"
        write_jsonl(normalized_path, normalized)

    meta = {
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "command": result.command,
        "returncode": result.returncode,
        "capture_mode": capture_mode,
        "session_dir": str(output_dir),
        "has_raw_jsonl": raw_jsonl_path is not None,
        "has_normalized_jsonl": normalized_path is not None,
    }
    if metadata:
        meta.update(metadata)
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return SavedCapturePaths(
        session_dir=output_dir,
        prompt_path=prompt_path,
        raw_stdout_path=raw_stdout_path,
        raw_stderr_path=raw_stderr_path,
        raw_jsonl_path=raw_jsonl_path,
        normalized_path=normalized_path,
        meta_path=meta_path,
    )


def _looks_like_json(line: str) -> bool:
    try:
        json.loads(line)
        return True
    except json.JSONDecodeError:
        return False
