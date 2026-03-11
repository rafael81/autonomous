from pathlib import Path

from autonomos.app import extract_final_message
from autonomos.io import write_jsonl


def test_extract_final_message_reads_last_assistant_message(tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"ts": "1", "source": "fixture", "channel": "x", "event_type": "assistant_message", "turn_id": "t1", "message_id": "m1", "call_id": None, "payload": {"text": "first"}, "raw": {}},
            {"ts": "2", "source": "fixture", "channel": "x", "event_type": "assistant_message", "turn_id": "t1", "message_id": "m2", "call_id": None, "payload": {"text": "second"}, "raw": {}},
        ],
    )

    assert extract_final_message(normalized) == "second"


def test_extract_final_message_synthesizes_when_runtime_returns_empty_placeholder(tmp_path: Path):
    normalized = tmp_path / "normalized.jsonl"
    write_jsonl(
        normalized,
        [
            {"ts": "1", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": "t1", "message_id": None, "call_id": "c1", "payload": {"tool_name": "list_dir", "output": "dir\tsrc\nfile\tREADME.md"}, "raw": {}},
            {"ts": "2", "source": "fixture", "channel": "tool", "event_type": "tool_call_result", "turn_id": "t1", "message_id": None, "call_id": "c2", "payload": {"tool_name": "read_file", "output": "1: # autonomos\n2: intro"}, "raw": {}},
            {"ts": "3", "source": "fixture", "channel": "assistant", "event_type": "assistant_message", "turn_id": "t1", "message_id": "m1", "call_id": None, "payload": {"text": "요청을 처리했지만 텍스트 응답이 없습니다."}, "raw": {}},
        ],
    )

    message = extract_final_message(normalized)

    assert message is not None
    assert "Observed workspace structure:" in message
    assert "list_dir" in message
    assert "read_file" in message
