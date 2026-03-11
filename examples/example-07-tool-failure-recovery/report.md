# example-07-tool-failure-recovery

## Input Prompt
Try a tool that fails, then explain next steps.

## Observation Summary
- total normalized events: 10
- event types: {'assistant_message': 1, 'session_end': 1, 'session_start': 1, 'task_complete': 1, 'task_started': 1, 'tool_call_error': 1, 'tool_call_request': 2, 'tool_call_result': 1, 'user_input': 1}

## Event Timeline
1. 2026-03-11T00:00:00Z session_start
2. 2026-03-11T00:00:01Z user_input: Try a tool that fails, then explain next steps.
3. 2026-03-11T00:00:02Z task_started
4. 2026-03-11T00:00:03Z tool_call_request
5. 2026-03-11T00:00:04Z tool_call_result
6. 2026-03-11T00:00:04Z tool_call_request
7. 2026-03-11T00:00:05Z tool_call_error
8. 2026-03-11T00:00:10Z assistant_message: One tool failed, so I explained the failure and suggested a fallback.
9. 2026-03-11T00:00:11Z task_complete
10. 2026-03-11T00:00:12Z session_end

## Tool Call Order
- tool_call_request (call-1)
- tool_call_result (call-1)
- tool_call_request (call-2)
- tool_call_error (call-2)

## Assistant Message Flow
- One tool failed, so I explained the failure and suggested a fallback.

## Final Result
One tool failed, so I explained the failure and suggested a fallback.

## Notes
Includes tool failure across call-1, call-2.
