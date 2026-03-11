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
