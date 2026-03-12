from pathlib import Path

from autonomos.io import write_jsonl
from autonomos.policy import infer_prompt_policy, rank_roma_attempt
from autonomos.roma_runtime import RomaAttemptResult, RomaChatResult
from autonomos.strategy import choose_strategy


def test_infer_prompt_policy_for_repository_inspection():
    policy = infer_prompt_policy("현재 프로젝트 구조 분석")

    assert policy.prompt_mode == "structure_inspection"
    assert policy.tool_budget == 5
    assert "src" in policy.preferred_roots
    assert "captures" in policy.excluded_roots


def test_infer_prompt_policy_for_repository_analysis():
    policy = infer_prompt_policy("현재 내 프로젝트 분석")

    assert policy.prompt_mode == "repository_inspection"
    assert policy.tool_budget == 5
    assert policy.preferred_tools[0] == "list_dir"


def test_infer_prompt_policy_for_code_review():
    policy = infer_prompt_policy("Review the current code changes.")

    assert policy.prompt_mode == "code_review"
    assert policy.preferred_tools[0] == "bash"


def test_rank_roma_attempt_penalizes_empty_runtime_fallback(tmp_path: Path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    empty_normalized = empty_dir / "normalized.jsonl"
    write_jsonl(
        empty_normalized,
        [
            {
                "ts": "",
                "source": "fixture",
                "channel": "assistant",
                "event_type": "assistant_message",
                "turn_id": None,
                "message_id": None,
                "call_id": None,
                "payload": {"text": "요청을 처리했지만 텍스트 응답이 없습니다."},
                "raw": {},
            },
        ],
    )
    observed_dir = tmp_path / "observed"
    observed_dir.mkdir()
    observed_normalized = observed_dir / "normalized.jsonl"
    write_jsonl(
        observed_normalized,
        [
            {
                "ts": "",
                "source": "fixture",
                "channel": "tool",
                "event_type": "tool_call_request",
                "turn_id": None,
                "message_id": None,
                "call_id": "c1",
                "payload": {"tool_name": "list_dir"},
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
                "payload": {"text": "Observed src and tests directories."},
                "raw": {},
            },
        ],
    )

    empty_attempt = RomaAttemptResult(
        result=RomaChatResult(
            final_message=None,
            session_dir=empty_dir,
            normalized_path=empty_normalized,
            raw_jsonl_path=empty_dir / "raw.jsonl",
            stdout_path=empty_dir / "stdout.txt",
            stderr_path=empty_dir / "stderr.txt",
            meta_path=empty_dir / "meta.json",
        ),
        strategy=choose_strategy("현재 프로젝트 구조 분석"),
        comparison_score=1,
        comparison_matches=0,
    )
    observed_attempt = RomaAttemptResult(
        result=RomaChatResult(
            final_message="Observed src and tests directories.",
            session_dir=observed_dir,
            normalized_path=observed_normalized,
            raw_jsonl_path=observed_dir / "raw.jsonl",
            stdout_path=observed_dir / "stdout.txt",
            stderr_path=observed_dir / "stderr.txt",
            meta_path=observed_dir / "meta.json",
        ),
        strategy=choose_strategy("현재 프로젝트 구조 분석"),
        comparison_score=2,
        comparison_matches=0,
    )

    assert rank_roma_attempt("현재 프로젝트 구조 분석", observed_attempt) < rank_roma_attempt(
        "현재 프로젝트 구조 분석",
        empty_attempt,
    )
