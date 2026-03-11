from pathlib import Path

from autonomos.fixtures import normalize_tui_fixture


FIXTURE_PATH = Path("/Users/user/project/codex/codex-rs/tui/tests/fixtures/oss-story.jsonl")


def test_normalize_tui_fixture_covers_required_story_events():
    events = normalize_tui_fixture(FIXTURE_PATH)
    event_types = [event["event_type"] for event in events]

    assert "session_start" in event_types
    assert "user_input" in event_types
    assert "task_started" in event_types
    assert "assistant_message_delta" in event_types
    assert "assistant_message" in event_types
    assert "task_complete" in event_types
    assert "session_end" in event_types


def test_first_user_turn_recovers_hello_prompt():
    events = normalize_tui_fixture(FIXTURE_PATH)
    first_user_input = next(event for event in events if event["event_type"] == "user_input")

    assert first_user_input["payload"]["text"] == "hello"
