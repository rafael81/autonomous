from pathlib import Path

from autonomos.io import write_jsonl
from autonomos.policy import rank_roma_attempt
from autonomos.roma_runtime import RomaAttemptResult, RomaChatResult
from autonomos.strategy import choose_strategy


def test_rank_roma_attempt_prefers_evidence_backed_project_analysis(tmp_path: Path):
    tool_dir = tmp_path / "tool"
    tool_dir.mkdir()
    tool_normalized = tool_dir / "normalized.jsonl"
    write_jsonl(
        tool_normalized,
        [
            {
                "ts": "",
                "source": "fixture",
                "channel": "tool",
                "event_type": "tool_call_request",
                "turn_id": None,
                "message_id": None,
                "call_id": "c1",
                "payload": {"tool_name": "bash"},
                "raw": {},
            },
            {
                "ts": "",
                "source": "fixture",
                "channel": "assistant",
                "event_type": "assistant_message",
                "turn_id": None,
                "message_id": None,
                "call_id": None,
                "payload": {"text": "테스트는 67 passed였고 CLI 구조와 workflow를 확인했습니다."},
                "raw": {},
            },
        ],
    )
    planning_dir = tmp_path / "planning"
    planning_dir.mkdir()
    planning_normalized = planning_dir / "normalized.jsonl"
    write_jsonl(
        planning_normalized,
        [
            {
                "ts": "",
                "source": "fixture",
                "channel": "assistant",
                "event_type": "assistant_message",
                "turn_id": None,
                "message_id": None,
                "call_id": None,
                "payload": {"text": "현재는 분석을 보류하고 실행 계획을 드립니다."},
                "raw": {},
            },
        ],
    )

    tool_attempt = RomaAttemptResult(
        result=RomaChatResult(
            final_message="테스트는 67 passed였고 CLI 구조와 workflow를 확인했습니다.",
            session_dir=tool_dir,
            normalized_path=tool_normalized,
            raw_jsonl_path=tool_dir / "raw.jsonl",
            stdout_path=tool_dir / "stdout.txt",
            stderr_path=tool_dir / "stderr.txt",
            meta_path=tool_dir / "meta.json",
        ),
        strategy=choose_strategy("현재 내 프로젝트 분석"),
        comparison_score=3,
        comparison_matches=0,
    )
    planning_attempt = RomaAttemptResult(
        result=RomaChatResult(
            final_message="현재는 분석을 보류하고 실행 계획을 드립니다.",
            session_dir=planning_dir,
            normalized_path=planning_normalized,
            raw_jsonl_path=planning_dir / "raw.jsonl",
            stdout_path=planning_dir / "stdout.txt",
            stderr_path=planning_dir / "stderr.txt",
            meta_path=planning_dir / "meta.json",
        ),
        strategy=choose_strategy("현재 내 프로젝트 분석"),
        comparison_score=2,
        comparison_matches=0,
    )

    assert rank_roma_attempt("현재 내 프로젝트 분석", tool_attempt) < rank_roma_attempt(
        "현재 내 프로젝트 분석",
        planning_attempt,
    )
