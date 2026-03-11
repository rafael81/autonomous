# example-03-single-tool

## Input Prompt
Run one tool and summarize.

## Observation Summary
- total normalized events: 8
- event types: {'assistant_message': 1, 'session_end': 1, 'session_start': 1, 'task_complete': 1, 'task_started': 1, 'tool_call_request': 1, 'tool_call_result': 1, 'user_input': 1}

## Event Timeline
1. 2026-03-11T00:00:00Z session_start
2. 2026-03-11T00:00:01Z user_input: Run one tool and summarize.
3. 2026-03-11T00:00:02Z task_started
4. 2026-03-11T00:00:03Z tool_call_request
5. 2026-03-11T00:00:04Z tool_call_result
6. 2026-03-11T00:00:10Z assistant_message: I checked the tool outputs and summarized the result.
7. 2026-03-11T00:00:11Z task_complete
8. 2026-03-11T00:00:12Z session_end

## Tool Call Order
- tool_call_request (call-1)
- tool_call_result (call-1)

## Assistant Message Flow
- I checked the tool outputs and summarized the result.

## Final Result
I checked the tool outputs and summarized the result.

## Notes
Single tool call: call-1
