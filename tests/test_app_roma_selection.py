from pathlib import Path

from autonomos.app import _rank_roma_attempt
from autonomos.io import write_jsonl
from autonomos.roma_runtime import RomaAttemptResult, RomaChatResult
from autonomos.strategy import choose_strategy


def test_rank_roma_attempt_prefers_tool_backed_inspection_answer(tmp_path: Path):
    planning_dir = tmp_path / "planning"
    planning_dir.mkdir()
    planning_normalized = planning_dir / "normalized.jsonl"
    write_jsonl(
        planning_normalized,
        [
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "You can run ls -la and sed -n '1,20p' README.md yourself."}, "raw": {}},
        ],
    )
    tool_dir = tmp_path / "tool"
    tool_dir.mkdir()
    tool_normalized = tool_dir / "normalized.jsonl"
    write_jsonl(
        tool_normalized,
        [
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_request", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "list_dir"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "list_dir"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "README.md exists."}, "raw": {}},
        ],
    )

    planning_attempt = RomaAttemptResult(
        result=RomaChatResult(
            final_message="fallback",
            session_dir=planning_dir,
            normalized_path=planning_normalized,
            raw_jsonl_path=planning_dir / "raw.jsonl",
            stdout_path=planning_dir / "stdout.txt",
            stderr_path=planning_dir / "stderr.txt",
            meta_path=planning_dir / "meta.json",
        ),
        strategy=choose_strategy("Make a plan for checking this repository"),
        comparison_score=2,
        comparison_matches=0,
    )
    tool_attempt = RomaAttemptResult(
        result=RomaChatResult(
            final_message="observed",
            session_dir=tool_dir,
            normalized_path=tool_normalized,
            raw_jsonl_path=tool_dir / "raw.jsonl",
            stdout_path=tool_dir / "stdout.txt",
            stderr_path=tool_dir / "stderr.txt",
            meta_path=tool_dir / "meta.json",
        ),
        strategy=choose_strategy("Check what files are in the repository"),
        comparison_score=3,
        comparison_matches=0,
    )

    assert _rank_roma_attempt(
        "List the top-level files in this repository and then read the first 20 lines of README.md.",
        tool_attempt,
    ) < _rank_roma_attempt(
        "List the top-level files in this repository and then read the first 20 lines of README.md.",
        planning_attempt,
    )
