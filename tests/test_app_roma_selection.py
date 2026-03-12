from pathlib import Path

from autonomos.io import write_jsonl
from autonomos.policy import rank_roma_attempt
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

    assert rank_roma_attempt(
        "List the top-level files in this repository and then read the first 20 lines of README.md.",
        tool_attempt,
    ) < rank_roma_attempt(
        "List the top-level files in this repository and then read the first 20 lines of README.md.",
        planning_attempt,
    )


def test_rank_roma_attempt_prefers_tool_backed_placeholder_over_access_fallback(tmp_path: Path):
    planning_dir = tmp_path / "planning2"
    planning_dir.mkdir()
    planning_normalized = planning_dir / "normalized.jsonl"
    write_jsonl(
        planning_normalized,
        [
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "I’m unable to execute shell commands directly in this environment, so I can’t fetch the live directory listing or read files right now."}, "raw": {}},
        ],
    )
    tool_dir = tmp_path / "tool2"
    tool_dir.mkdir()
    tool_normalized = tool_dir / "normalized.jsonl"
    write_jsonl(
        tool_normalized,
        [
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_request", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "list_dir"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "list_dir", "output": "file\tREADME.md\ndir\tsrc"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_request", "turn_id": None, "message_id": None, "call_id": "c2", "payload": {"tool_name": "read_file"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": None, "message_id": None, "call_id": "c2", "payload": {"tool_name": "read_file", "output": "1: # autonomos\n2: intro"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "요청을 처리했지만 텍스트 응답이 없습니다."}, "raw": {}},
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
        comparison_score=3,
        comparison_matches=0,
    )
    tool_attempt = RomaAttemptResult(
        result=RomaChatResult(
            final_message="요청을 처리했지만 텍스트 응답이 없습니다.",
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

    assert rank_roma_attempt(
        "List the top-level files in this repository and then read the first 20 lines of README.md.",
        tool_attempt,
    ) < rank_roma_attempt(
        "List the top-level files in this repository and then read the first 20 lines of README.md.",
        planning_attempt,
    )


def test_rank_roma_attempt_prefers_tool_backed_review_attempt(tmp_path: Path):
    planning_dir = tmp_path / "planning-review"
    planning_dir.mkdir()
    planning_normalized = planning_dir / "normalized.jsonl"
    write_jsonl(
        planning_normalized,
        [
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "Here is a review plan with prioritized findings."}, "raw": {}},
        ],
    )
    tool_dir = tmp_path / "tool-review"
    tool_dir.mkdir()
    tool_normalized = tool_dir / "normalized.jsonl"
    write_jsonl(
        tool_normalized,
        [
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_request", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": None, "message_id": None, "call_id": "c1", "payload": {"tool_name": "bash", "output": "diff"}, "raw": {}},
            {"ts": "", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": None, "message_id": None, "call_id": None, "payload": {"text": "Prioritized findings:\n- issue"}, "raw": {}},
        ],
    )

    planning_attempt = RomaAttemptResult(
        result=RomaChatResult(
            final_message="plan",
            session_dir=planning_dir,
            normalized_path=planning_normalized,
            raw_jsonl_path=planning_dir / "raw.jsonl",
            stdout_path=planning_dir / "stdout.txt",
            stderr_path=planning_dir / "stderr.txt",
            meta_path=planning_dir / "meta.json",
        ),
        strategy=choose_strategy("Make a plan for reviewing these changes"),
        comparison_score=0,
        comparison_matches=0,
    )
    tool_attempt = RomaAttemptResult(
        result=RomaChatResult(
            final_message="review",
            session_dir=tool_dir,
            normalized_path=tool_normalized,
            raw_jsonl_path=tool_dir / "raw.jsonl",
            stdout_path=tool_dir / "stdout.txt",
            stderr_path=tool_dir / "stderr.txt",
            meta_path=tool_dir / "meta.json",
        ),
        strategy=choose_strategy("Review only the current CLI changes."),
        comparison_score=0,
        comparison_matches=0,
    )

    assert rank_roma_attempt(
        "Review only the current CLI changes.",
        tool_attempt,
    ) < rank_roma_attempt(
        "Review only the current CLI changes.",
        planning_attempt,
    )
