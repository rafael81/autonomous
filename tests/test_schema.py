from autonomos.schema import NORMALIZED_EVENT_REQUIRED_FIELDS, build_event


def test_build_event_has_required_fields():
    event = build_event(
        ts="2025-01-01T00:00:00Z",
        source="fixture",
        channel="tui",
        event_type="session_start",
        payload={"model": "test"},
        raw={"kind": "session_start"},
    )

    assert tuple(event.keys()) == NORMALIZED_EVENT_REQUIRED_FIELDS
    assert event["turn_id"] is None
    assert event["message_id"] is None
    assert event["call_id"] is None
