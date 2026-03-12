from autonomos.compare import compare_normalized_sequences


def test_compare_normalized_sequences_ignores_tool_profiles_and_deltas():
    expected = [
        {"event_type": "session_start", "payload": {}},
        {"event_type": "user_input", "payload": {}},
        {"event_type": "task_started", "payload": {}},
        {"event_type": "tool_call_request", "payload": {"tool_name": "list_dir"}},
        {"event_type": "tool_call_result", "payload": {"tool_name": "list_dir"}},
        {"event_type": "assistant_message_delta", "payload": {"text": "hello"}},
        {"event_type": "assistant_message", "payload": {"text": "final"}},
        {"event_type": "task_complete", "payload": {}},
        {"event_type": "session_end", "payload": {}},
    ]
    actual = [
        {"event_type": "session_start", "payload": {}},
        {"event_type": "user_input", "payload": {}},
        {"event_type": "task_started", "payload": {}},
        {"event_type": "tool_profile", "payload": {"tool_name": "list_dir"}},
        {"event_type": "tool_call_request", "payload": {"tool_name": "list_dir"}},
        {"event_type": "tool_call_result", "payload": {"tool_name": "list_dir"}},
        {"event_type": "assistant_message", "payload": {"text": "final"}},
        {"event_type": "task_complete", "payload": {}},
        {"event_type": "session_end", "payload": {}},
    ]

    result = compare_normalized_sequences(expected, actual)

    assert result.matches is True
    assert result.score == 0


def test_compare_normalized_sequences_ignores_user_input():
    expected = [
        {"event_type": "session_start", "payload": {}},
        {"event_type": "task_started", "payload": {}},
        {"event_type": "assistant_message", "payload": {"text": "final"}},
        {"event_type": "task_complete", "payload": {}},
        {"event_type": "session_end", "payload": {}},
    ]
    actual = [
        {"event_type": "session_start", "payload": {}},
        {"event_type": "user_input", "payload": {"text": "hello"}},
        {"event_type": "task_started", "payload": {}},
        {"event_type": "assistant_message", "payload": {"text": "final"}},
        {"event_type": "task_complete", "payload": {}},
        {"event_type": "session_end", "payload": {}},
    ]

    result = compare_normalized_sequences(expected, actual)

    assert result.matches is True
    assert result.score == 0
