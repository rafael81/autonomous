from autonomos.compare import compare_normalized_sequences
from autonomos.schema import build_event


def _event(event_type: str, **payload: str) -> dict:
    return build_event(
        ts="2026-03-11T00:00:00Z",
        source="fixture",
        channel="cli",
        event_type=event_type,
        turn_id="turn-1",
        payload=payload,
        raw={"kind": event_type},
    )


def test_compare_accepts_same_structure():
    expected = [_event("session_start"), _event("user_input", text="hi"), _event("assistant_message", text="hello")]
    actual = [_event("session_start"), _event("user_input", text="bye"), _event("assistant_message", text="different wording")]

    result = compare_normalized_sequences(expected, actual)

    assert result.matches is True
    assert result.score == 0


def test_compare_rejects_different_tool_sequence():
    expected = [_event("session_start"), _event("tool_call_request", tool_name="shell"), _event("assistant_message", text="ok")]
    actual = [_event("session_start"), _event("request_user_input"), _event("assistant_message", text="ok")]

    result = compare_normalized_sequences(expected, actual)

    assert result.matches is False
    assert result.score > 0
    assert any("tool orchestration differs" in detail or "event type sequence differs" in detail for detail in result.details)
