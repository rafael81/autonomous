from autonomos.delta import analyze_trace_drift


def test_analyze_trace_drift_reports_tool_routing_and_final_formatting():
    expected = [
        {"event_type": "session_start", "payload": {}},
        {"event_type": "user_input", "payload": {}},
        {"event_type": "task_started", "payload": {}},
        {"event_type": "tool_call_request", "payload": {"tool_name": "list_dir"}},
        {"event_type": "tool_call_result", "payload": {"tool_name": "list_dir"}},
        {"event_type": "assistant_message", "payload": {"text": "Summary:\n- one\n- two"}},
        {"event_type": "task_complete", "payload": {}},
        {"event_type": "session_end", "payload": {}},
    ]
    actual = [
        {"event_type": "session_start", "payload": {}},
        {"event_type": "user_input", "payload": {}},
        {"event_type": "task_started", "payload": {}},
        {"event_type": "tool_call_request", "payload": {"tool_name": "bash"}},
        {"event_type": "tool_call_result", "payload": {"tool_name": "bash"}},
        {"event_type": "assistant_message", "payload": {"text": "Short answer."}},
        {"event_type": "task_complete", "payload": {}},
        {"event_type": "session_end", "payload": {}},
    ]

    analysis = analyze_trace_drift(expected, actual)

    assert "tool_routing" in analysis.primary_causes
    assert any(category.name == "final_answer_formatting" for category in analysis.categories)


def test_analyze_trace_drift_reports_artifact_drift():
    expected = [
        {"event_type": "request_user_input", "payload": {"questions": 1}},
        {"event_type": "assistant_message", "payload": {"text": "Please choose."}},
    ]
    actual = [
        {"event_type": "assistant_message", "payload": {"text": "I picked for you."}},
    ]

    analysis = analyze_trace_drift(expected, actual)

    assert any(category.name == "user_input_artifacts" for category in analysis.categories)


def test_analyze_trace_drift_summarizes_inspection_family_mismatch():
    expected = (
        [{"event_type": "tool_call_request", "payload": {"tool_name": "shell"}} for _ in range(6)]
        + [{"event_type": "tool_call_result", "payload": {"tool_name": "shell"}} for _ in range(6)]
    )
    actual = (
        [{"event_type": "tool_call_request", "payload": {"tool_name": "list_dir"}} for _ in range(2)]
        + [{"event_type": "tool_call_result", "payload": {"tool_name": "list_dir"}} for _ in range(2)]
    )

    analysis = analyze_trace_drift(expected, actual)

    assert "shorter built-in tool path" in analysis.summary
    lines = analysis.summary.split("; ")
    assert any("inspection evidence was gathered with fewer tool calls" in line for line in lines)
