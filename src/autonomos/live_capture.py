"""Live process capture helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LiveCaptureResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


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
