# roma-project-structure-analysis

## Input Prompt
현재 프로젝트 구조 분석

## Observation Summary
- total normalized events: 40
- event types: {'assistant_message': 1, 'assistant_message_delta': 34, 'session_end': 1, 'session_start': 1, 'task_complete': 1, 'task_started': 1, 'user_input': 1}

## Event Timeline
1.  session_start
2.  user_input: Observed project-analysis evidence:

Initial scan:
/Users/user/project/autonomos
3.  task_started
4.  assistant_message_delta: 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1)
5.  assistant_message_delta: 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1)
6.  assistant_message_delta: 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1)
7.  assistant_message_delta: 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1)
8.  assistant_message_delta: 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1)
9.  assistant_message_delta: 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1)
10.  assistant_message_delta: 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1)
11.  assistant_message_delta: 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1)
12.  assistant_message_delta: 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1)

## Tool Call Order
- none

## Assistant Message Flow
- 좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1) 전체 아키텍처 구조(요약)

현재 `autonomos`는 크게 4층 구조입니다.

1. **CLI 진입층**
   - `src/autonomo

## Final Result
좋습니다. 요청하신 **“현재 프로젝트 구조 분석”** 기준으로, 코드베이스를 **구조/흐름/책임 분리** 관점에서 정리해드릴게요.

## 1) 전체 아키텍처 구조(요약)

현재 `autonomos`는 크게 4층 구조입니다.

1. **CLI 진입층**
   - `src/autonomos/cli.py`
   - `argparse` 기반 서브커맨드(약 15개)로 모든 기능을 노출
   - 사용자 명령을 각 기능 모듈로 위임

2. **워크플로우/어플리케이션층**
   - `src/autonomos/app.py` (채팅 사용자 플로우)
   - `src/autonomos/workflow.py` (관측/캡처/재시도/요약 루프)
   - 전략·정책 판단 + 비교기반 적응 로직이 핵심

3. **실행/적응/정규화 인터페이스층**
   - `src/autonomos/codex_exec.py` (openai_ws 실행 명령 빌드 등)
   - `src/autonomos/roma_runtime.py` (roma websocket 브릿지 실행 + 정규화)
   - `src/autonomos/live_capture.py`, `exec_normalizer.py`, `schema.py`, `compare.py`, `baseline.py`

4. **기록/기억/보고/유틸층**
   - `src/autonomos/memory.py`, `reports.py`, `adaptive.py`, `io.py`, `transcript` 관련 유틸(내포됨)

---

## 2) 핵심 파일/모듈 책임 맵

### `cli.py`
- 명령어 라우팅 중심 파일.
- 제공 커맨드:  
  `version`, `build-examples`, `print-ws-config`, `capture-live`, `normalize-exec`, `compare`, `observe`, `chat`, `resume`, `repl`, `sessions`, `transcript` 등.
- `chat` 기본 런타임은 `roma_ws` (README와 일치).

### `app.py` (run_chat)
- 사용자 대화형 경로 전용.
- 기억(memory) + 정책/전략 조합 + 실행 + 비교 + 요약 + 아티팩트 생성까지 묶는 상위 오케스트레이션.
- `roma_ws`면 `run_roma_chat` 직접 호출, 아니면 `observe_prompt`로 폴백.

### `workflow.py` (observe_prompt)
- 실제 **다중 시도(candidate strategies)** 기반 관측 파이프라인.
- 시도별로:
  1. 정책 가이드 생성
  2. 실행 명령 생성(`build_exec_command`)
  3. 캡처 저장(`save_capture_session`)
  4. baseline 비교
  5. 오케스트레이션 판정(재시도/요청/승인)
- 모든 시도 결과를 점수화해 최적 시도 선택.

### `strategy.py`
- `choose_strategy` + `candidate_strategies` 로 요청 분류.
- 전략 ID: `simple_answer`, `long_form`, `tool_oriented`, `planning`, `safety_refusal`
- 각 전략은 baseline ID/안내 프롬프트/샌드박스 모드 등 포함.

### `policy.py`
- prompt별 실행정책(`PromptPolicy`) 산출:
  - `project_analysis`, `repository_inspection`, `verification`, `inspection_and_verification` 등
- 정책을 텍스트 가이드 문자열로 만들어 실제 프롬프트에 주입.

### `orchestration.py`
- 재시도/요청/승인 조건 결정:
  - `decide_orchestration`이 비교 점수 기준, 입력 텍스트 기반으로 `should_retry`, `should_request_user_input` 판정.
- 요청/승인 아티팩트(JSON) 생성 및 응답 렌더링.

### `roma_runtime.py`
- Node 기반 브릿지(`roma_bridge.mjs`) 호출.
- stdout JSONL 이벤트를 파싱해 `normalized.jsonl`로 정규화.
- 세션 메타/원본/출력/에러 로그 저장.

---

## 3) 프로젝트 트리(실무적으로 중요한 부분만)

- `src/autonomos/`  
  - CLI: `cli.py`
  - 사용자 플로우: `app.py`
  - 워크플로우: `workflow.py`
  - 런타임: `roma_runtime.py`, `codex_exec.py`, `live_capture.py`
  - 전략/정책: `strategy.py`, `policy.py`, `orchestration.py`
  - 비교/정규화: `baseline.py`, `compare.py`, `exec_normalizer.py`, `schema.py`
  - 메모리/보고/유틸: `memory.py`, `reports.py`, `io.py`, `adaptive.py`, `project_analysis.py` 등
- `tests/`
  - `test_cli.py`: CLI 동작/입력검증
  - `test_workflow.py`: 다중 시도, 폴백, 아티팩트 생성 흐름 검증
- 데이터/아티팩트 폴더:
  - `fixtures/`, `examples/`, `captures/`, `examples_live/`
- 설정:
  - `pyproject.toml` + `README.md`

---

## 4) 데이터 흐름(핵심)

- `chat`:
  - 사용자 입력 → `cli` → `run_chat` → (전략/정책 주입) → `run_roma_chat` 또는 `observe_prompt` → baseline 비교 → best attempt 선택 → 답변/요약/기억 저장/아티팩트 생성.
- `observe`:
  - 사용자 입력 → `observe_prompt` → 후보 전략 다중시도 실행 → baseline 비교 점수 기반 best attempt 선택 → promote + comparison-summary 생성.
- 공통 아티팩트:
  - `raw.jsonl`, `stdout.txt`, `stderr.txt`, `prompt.txt`, `normalized.jsonl`, `meta.json`
  - 성공/실패 모두 비교 및 추적 가능.

---

## 5) 현재 상태에서의 강점/위험 포인트

### 강점
- 모듈 분리가 비교적 명확함(입출력-정책-실행-비교-보고).
- 테스트가 69개 통과(현재는 기본 플로우 안정성 우수).
- 전략/정책/오케스트레이션이 분리되어 확장성 있음.
- 채팅/관측 파이프라인이 baseline 적응 루프를 공유.

### 위험/주의
- `roma_runtime.py`의 `DEFAULT_ROMA_ROOT`가 절대 경로로 하드코딩되어 이동성/CI 이식성 제약.
- 런타임 이벤트 파싱은 line-by-line JSON 가정에 강하게 의존(예외 처리 보강 여지).
- 프로젝트 루트에서의 동작 가정이 여러 모듈에서 암묵적일 수 있음(경로 기반 로직 검토 필요).
- `chat` 경로와 `observe` 경로 일부 공통 로직이 병렬되어 있어 drift 가능성 존재(향후 통합 리팩터링 고려).

---

필요하시면 이어서 **“모듈 간 의존도 그래프(함수 호출 레벨)”**나 **“명령어별 실패 모드(오류 시 어디서 터지는지)”**를 중심으로 더 깊게 분석해드릴게요.

## Notes
Imported from a real normalized trace.
