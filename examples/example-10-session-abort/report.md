# example-10-session-abort

## Input Prompt
Start a task, then stop.

## Observation Summary
- total normalized events: 6
- event types: {'assistant_message': 1, 'session_end': 1, 'session_start': 1, 'task_complete': 1, 'task_started': 1, 'user_input': 1}

## Event Timeline
1. 2026-03-11T00:00:00Z session_start
2. 2026-03-11T00:00:01Z user_input: Start a task, then stop.
3. 2026-03-11T00:00:02Z task_started
4. 2026-03-11T00:00:10Z assistant_message: The session was interrupted before a full answer was completed.
5. 2026-03-11T00:00:11Z task_complete
6. 2026-03-11T00:00:12Z session_end

## Tool Call Order
- none

## Assistant Message Flow
- The session was interrupted before a full answer was completed.

## Final Result
The session was interrupted before a full answer was completed.

## Notes
Represents interrupted or early-ended session.
