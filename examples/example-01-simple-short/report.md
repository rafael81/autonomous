# example-01-simple-short

## Input Prompt
Say hello briefly.

## Observation Summary
- total normalized events: 13
- event types: {'assistant_message': 1, 'assistant_message_delta': 7, 'session_end': 1, 'session_start': 1, 'task_complete': 1, 'task_started': 1, 'user_input': 1}

## Event Timeline
1. 2026-03-11T00:00:00Z session_start
2. 2026-03-11T00:00:01Z user_input: Say hello briefly.
3. 2026-03-11T00:00:02Z task_started
4. 2026-03-11T00:00:03Z assistant_message_delta: Hello!
5. 2026-03-11T00:00:04Z assistant_message_delta:  How
6. 2026-03-11T00:00:05Z assistant_message_delta:  can
7. 2026-03-11T00:00:06Z assistant_message_delta:  I
8. 2026-03-11T00:00:07Z assistant_message_delta:  help
9. 2026-03-11T00:00:08Z assistant_message_delta:  you
10. 2026-03-11T00:00:09Z assistant_message_delta:  today?
11. 2026-03-11T00:00:10Z assistant_message: Hello! How can I help you today?
12. 2026-03-11T00:00:11Z task_complete

## Tool Call Order
- none

## Assistant Message Flow
- Hello! How can I help you today?

## Final Result
Hello! How can I help you today?

## Notes
Short direct answer.
