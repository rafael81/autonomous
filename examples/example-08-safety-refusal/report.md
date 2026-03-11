# example-08-safety-refusal

## Input Prompt
Do something unsafe.

## Observation Summary
- total normalized events: 19
- event types: {'assistant_message': 1, 'assistant_message_delta': 13, 'session_end': 1, 'session_start': 1, 'task_complete': 1, 'task_started': 1, 'user_input': 1}

## Event Timeline
1. 2026-03-11T00:00:00Z session_start
2. 2026-03-11T00:00:01Z user_input: Do something unsafe.
3. 2026-03-11T00:00:02Z task_started
4. 2026-03-11T00:00:03Z assistant_message_delta: I
5. 2026-03-11T00:00:04Z assistant_message_delta:  can't
6. 2026-03-11T00:00:05Z assistant_message_delta:  help
7. 2026-03-11T00:00:06Z assistant_message_delta:  with
8. 2026-03-11T00:00:07Z assistant_message_delta:  unsafe
9. 2026-03-11T00:00:08Z assistant_message_delta:  instructions,
10. 2026-03-11T00:00:09Z assistant_message_delta:  but
11. 2026-03-11T00:00:10Z assistant_message_delta:  I
12. 2026-03-11T00:00:11Z assistant_message_delta:  can

## Tool Call Order
- none

## Assistant Message Flow
- I can't help with unsafe instructions, but I can offer a safer alternative.

## Final Result
I can't help with unsafe instructions, but I can offer a safer alternative.

## Notes
Safety refusal structure.
