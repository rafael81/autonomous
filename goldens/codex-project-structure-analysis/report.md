# codex-project-structure-analysis

## Input Prompt
현재 프로젝트 구조 분석

## Observation Summary
- total normalized events: 130
- event types: {'assistant_message': 14, 'session_end': 1, 'session_start': 1, 'task_complete': 1, 'task_started': 1, 'tool_call_request': 56, 'tool_call_result': 56}

## Event Timeline
1.  session_start
2.  task_started
3.  assistant_message: 프로젝트 구조를 파악하겠습니다. 먼저 `bd` 온보딩과 최상위 파일/디렉터리, 핵심 설정 파일을 확인해서 기술 스택과 모듈 경계를 정리하겠습니다
4.  tool_call_request
5.  tool_call_result
6.  tool_call_request
7.  tool_call_request
8.  tool_call_result
9.  tool_call_result
10.  assistant_message: 최상위 구조를 보면 Python 패키지 본체는 `src/autonomos`에 있고, `tests`, `examples`, `goldens`, `
11.  tool_call_request
12.  tool_call_request

## Tool Call Order
- tool_call_request (item_1)
- tool_call_result (item_1)
- tool_call_request (item_2)
- tool_call_request (item_3)
- tool_call_result (item_2)
- tool_call_result (item_3)
- tool_call_request (item_5)
- tool_call_request (item_6)
- tool_call_request (item_7)
- tool_call_result (item_5)
- tool_call_result (item_7)
- tool_call_result (item_6)
- tool_call_request (item_9)
- tool_call_request (item_10)
- tool_call_request (item_11)
- tool_call_result (item_9)
- tool_call_result (item_10)
- tool_call_result (item_11)
- tool_call_request (item_13)
- tool_call_request (item_14)
- tool_call_request (item_15)
- tool_call_result (item_13)
- tool_call_result (item_14)
- tool_call_result (item_15)
- tool_call_request (item_16)
- tool_call_result (item_16)
- tool_call_request (item_18)
- tool_call_request (item_19)
- tool_call_request (item_20)
- tool_call_request (item_21)
- tool_call_result (item_18)
- tool_call_result (item_20)
- tool_call_result (item_19)
- tool_call_result (item_21)
- tool_call_request (item_23)
- tool_call_request (item_24)
- tool_call_request (item_25)
- tool_call_request (item_26)
- tool_call_result (item_23)
- tool_call_result (item_26)
- tool_call_result (item_24)
- tool_call_result (item_25)
- tool_call_request (item_28)
- tool_call_request (item_29)
- tool_call_request (item_30)
- tool_call_request (item_31)
- tool_call_request (item_32)
- tool_call_request (item_33)
- tool_call_result (item_28)
- tool_call_result (item_30)
- tool_call_result (item_33)
- tool_call_result (item_29)
- tool_call_result (item_32)
- tool_call_result (item_31)
- tool_call_request (item_34)
- tool_call_result (item_34)
- tool_call_request (item_35)
- tool_call_result (item_35)
- tool_call_request (item_37)
- tool_call_request (item_38)
- tool_call_request (item_39)
- tool_call_result (item_37)
- tool_call_result (item_38)
- tool_call_result (item_39)
- tool_call_request (item_41)
- tool_call_request (item_42)
- tool_call_request (item_43)
- tool_call_request (item_44)
- tool_call_request (item_45)
- tool_call_result (item_41)
- tool_call_result (item_43)
- tool_call_result (item_42)
- tool_call_result (item_44)
- tool_call_result (item_45)
- tool_call_request (item_47)
- tool_call_request (item_48)
- tool_call_request (item_49)
- tool_call_request (item_50)
- tool_call_result (item_47)
- tool_call_result (item_48)
- tool_call_result (item_50)
- tool_call_result (item_49)
- tool_call_request (item_52)
- tool_call_result (item_52)
- tool_call_request (item_54)
- tool_call_request (item_55)
- tool_call_request (item_56)
- tool_call_request (item_57)
- tool_call_request (item_58)
- tool_call_request (item_59)
- tool_call_result (item_55)
- tool_call_result (item_54)
- tool_call_result (item_58)
- tool_call_result (item_57)
- tool_call_result (item_56)
- tool_call_result (item_59)
- tool_call_request (item_60)
- tool_call_request (item_61)
- tool_call_request (item_62)
- tool_call_request (item_63)
- tool_call_request (item_64)
- tool_call_request (item_65)
- tool_call_request (item_66)
- tool_call_result (item_60)
- tool_call_result (item_61)
- tool_call_result (item_63)
- tool_call_result (item_62)
- tool_call_result (item_66)
- tool_call_result (item_64)
- tool_call_result (item_65)
- tool_call_request (item_67)
- tool_call_result (item_67)

## Assistant Message Flow
- 프로젝트 구조를 파악하겠습니다. 먼저 `bd` 온보딩과 최상위 파일/디렉터리, 핵심 설정 파일을 확인해서 기술 스택과 모듈 경계를 정리하겠습니다.
- 최상위 구조를 보면 Python 패키지 본체는 `src/autonomos`에 있고, `tests`, `examples`, `goldens`, `captures`가 별도로 붙어 있는 형태입니다. 이제 README와 엔트리포인트를 읽어서 이 저장소가 어떤 실행 흐름으로 묶여 있는지 확인하겠
- README와 설정을 보면 이 저장소는 "Codex CLI 관찰/정규화 툴킷"에 맞춰 설계돼 있습니다. 다음으로 CLI 명령 집합과 핵심 모듈의 책임을 확인해서 실제 구조를 기능 단위로 나누겠습니다.
- 엔트리포인트는 `cli.py` 하나에 집중돼 있고, 여기서 관찰 파이프라인, 채팅 런타임, 회귀 검증, 세션 관리까지 모두 라우팅합니다. 핵심 실행 흐름인 `chat`/`observe`가 어떤 모듈 조합으로 동작하는지 더 보겠습니다.
- 실행 흐름은 `chat`가 가장 상위 조합기이고, 내부에서 전략 선택, 정책 추론, 런타임 호출, baseline 비교, 메모리 저장까지 한 번에 묶습니다. 보조 모듈들이 어떤 책임으로 나뉘는지 확인하려고 전략/정책/오케스트레이션 계층도 읽고 있습니다.
- 이 프로젝트는 단순 CLI가 아니라, 실행 결과를 baseline과 비교해서 품질을 판단하는 평가용 구조가 강합니다. 그래서 example/golden/regression 쪽이 실제 제품 코드만큼 중요한 축인지 확인하고 있습니다.
- 평가 계층은 `examples`와 `goldens`를 기준점으로 두고 현재 런타임을 비교하는 형태입니다. 이제 추적 스키마와 외부 런타임 연결부를 보면, 저장소 구조를 더 정확히 설명할 수 있습니다.
- 구조 설명에 숫자를 붙이기 위해 디렉터리별 파일 분포도 확인하겠습니다. 이 저장소는 실행 코드보다 예제/캡처 데이터가 더 큰 비중인지가 중요합니다.
- `captures`와 `examples_live` 비중이 커서, 이 저장소는 "제품 코드 + 대량의 관찰 산출물"이 함께 들어 있는 형태입니다. 남은 핵심은 Codex/웹소켓 런타임 설정과 검증 모듈인데, 그 부분만 보고 전체 그림을 정리하겠습니다.
- 거의 전체 그림이 나왔습니다. 마지막으로 `fixtures`와 대표 테스트 구성을 한번만 확인하고, 바로 구조 분석을 정리하겠습니다.
- 구조상 중요한 점 하나가 보였습니다. 일부 런타임과 fixture가 외부 로컬 경로에 하드코딩돼 있어서, 저장소 단독으로는 완결되지 않을 수 있습니다. 이 부분만 정확히 확인하고 요약하겠습니다.
- 정리 단계입니다. 주요 엔트리포인트와 하드코딩 의존성에 대한 줄 번호만 확보한 뒤, 저장소 구조를 기능 축 기준으로 요약하겠습니다.
- 정리할 수준의 근거는 충분합니다. 구조, 실행 흐름, 평가 데이터 축, 그리고 포터빌리티 이슈까지 한 번에 묶어서 전달하겠습니다.
- 이 프로젝트는 "일반 애플리케이션"보다는 `Codex/ROMA 실행을 관찰하고, 정규화하고, baseline/golden과 비교하는 평가 툴킷`에 가깝습니다. README도 같은 방향으로 설명하고 있고, 핵심 사용 흐름을 `observe`, `chat`, `compare-baseline

## Final Result
이 프로젝트는 "일반 애플리케이션"보다는 `Codex/ROMA 실행을 관찰하고, 정규화하고, baseline/golden과 비교하는 평가 툴킷`에 가깝습니다. README도 같은 방향으로 설명하고 있고, 핵심 사용 흐름을 `observe`, `chat`, `compare-baselines`, `run-regression`으로 잡고 있습니다. [README.md#L3](/Users/user/project/autonomos/README.md#L3) [README.md#L43](/Users/user/project/autonomos/README.md#L43) [README.md#L73](/Users/user/project/autonomos/README.md#L73)

구조는 크게 4축입니다.
- 제품 코드: `src/autonomos` 아래 28개 Python 모듈이 있고, CLI 엔트리포인트는 [`src/autonomos/cli.py#L45`](/Users/user/project/autonomos/src/autonomos/cli.py#L45) 하나에 모여 있습니다. `chat`, `observe`, `review`, `resume`, `verify-runtime`, `run-regression` 같은 서브커맨드가 모두 여기서 라우팅됩니다. 패키징은 단순한 setuptools 기반이고 런타임 Python 의존성은 비어 있습니다. [pyproject.toml#L5](/Users/user/project/autonomos/pyproject.toml#L5) [pyproject.toml#L16](/Users/user/project/autonomos/pyproject.toml#L16)
- 실행 오케스트레이션: 실제 상위 흐름은 [`src/autonomos/app.py#L56`](/Users/user/project/autonomos/src/autonomos/app.py#L56)의 `run_chat`과 [`src/autonomos/workflow.py#L51`](/Users/user/project/autonomos/src/autonomos/workflow.py#L51)의 `observe_prompt`가 담당합니다. `run_chat`은 전략 선택, 정책 추론, ROMA 호출, baseline 비교, 메모리 저장까지 묶는 상위 조합기입니다.
- 전략/정책 계층: [`src/autonomos/strategy.py#L22`](/Users/user/project/autonomos/src/autonomos/strategy.py#L22)에서 `simple_answer`, `tool_oriented`, `planning`, `safety_refusal` 같은 전략을 고르고, [`src/autonomos/policy.py#L35`](/Users/user/project/autonomos/src/autonomos/policy.py#L35)에서 `structure_inspection`, `repository_inspection`, `code_review` 같은 정책으로 tool budget과 선호 도구를 결정합니다. 지금 요청 같은 "프로젝트 구조 분석"은 명시적으로 `tool_oriented`로 라우팅됩니다. [src/autonomos/strategy.py#L110](/Users/user/project/autonomos/src/autonomos/strategy.py#L110)
- 평가/데이터셋 계층: [`src/autonomos/baseline.py#L82`](/Users/user/project/autonomos/src/autonomos/baseline.py#L82)에서 capture를 example로 승격하고, [`src/autonomos/baseline.py#L168`](/Users/user/project/autonomos/src/autonomos/baseline.py#L168)에서 baseline 비교를 수행합니다. [`src/autonomos/regression.py#L77`](/Users/user/project/autonomos/src/autonomos/regression.py#L77)과 [`src/autonomos/verification.py#L23`](/Users/user/project/autonomos/src/autonomos/verification.py#L23)가 golden 기반 회귀/검증 러너입니다.

실행 런타임은 2갈래입니다.
- `observe` 계열은 `codex exec --json`을 호출하고 결과를 공통 JSONL 스키마로 정규화합니다. [src/autonomos/workflow.py#L83](/Users/user/project/autonomos/src/autonomos/workflow.py#L83)
- `chat` 기본값은 `roma_ws`이며, Node 브리지로 `roma-cli`를 호출합니다. [README.md#L59](/Users/user/project/autonomos/README.md#L59) [src/autonomos/roma_runtime.py#L42](/Users/user/project/autonomos/src/autonomos/roma_runtime.py#L42)
- 브리지 스크립트는 저장소 내부 `scripts/roma_bridge.mjs`지만, 실제 구현체 import는 외부 로컬 경로에 하드코딩돼 있습니다. [scripts/roma_bridge.mjs#L7](/Users/user/project/autonomos/scripts/roma_bridge.mjs#L7) [src/autonomos/roma_runtime.py#L19](/Users/user/project/autonomos/src/autonomos/roma_runtime.py#L19)
- 이 브리지는 `list_dir`, `search_files`, `read_file`, `grep_text`, `glob_paths`, `bash` 같은 로컬 inspection 도구를 제공하고, 구조 분석 모드에서는 `bash`를 막고 내장 inspection tool 위주로 유도합니다. [scripts/roma_bridge.mjs#L70](/Users/user/project/autonomos/scripts/roma_bridge.mjs#L70) [scripts/roma_bridge.mjs#L171](/Users/user/project/autonomos/scripts/roma_bridge.mjs#L171)

디렉터리 관점에서 보면 코드보다 관찰 산출물이 큰 비중입니다.
- `captures`: 804개 파일
- `examples_live`: 80개 파일
- `examples`: 50개 파일
- `goldens`: 50개 파일
- `codex_traces`: 12개 파일
- `tests`: 34개 파일
- `src/autonomos`: 28개 파일

해석하면 이 저장소는 "라이브 실행 결과를 축적하고, 예제화하고, 기준선과 비교하는 실험/평가 저장소" 성격이 강합니다. `tests`도 모듈 단위보다는 시나리오 단위가 많아서 `test_app_roma_*`, `test_resume_flow`, `test_orchestration_artifacts`처럼 런타임 흐름 검증이 중심입니다. [tests](/Users/user/project/autonomos/tests)

중요한 관찰사항도 있습니다.
- 포터빌리티가 낮습니다. `roma-cli`와 Codex fixture가 외부 절대경로에 묶여 있습니다. [src/autonomos/roma_runtime.py#L19](/Users/user/project/autonomos/src/autonomos/roma_runtime.py#L19) [scripts/roma_bridge.mjs#L7](/Users/user/project/autonomos/scripts/roma_bridge.mjs#L7) [src/autonomos/examples.py#L14](/Users/user/project/autonomos/src/autonomos/examples.py#L14)
- `fixtures/` 디렉터리는 현재 비어 있고, example 생성은 내부 fixture가 아니라 외부 Codex repo fixture를 참조합니다. [src/autonomos/examples.py#L117](/Users/user/project/autonomos/src/autonomos/examples.py#L117)
- `pyproject.toml`에는 Python 의존성이 거의 없지만, 실제 실행은 Node와 외부 `roma-cli` 환경에 의존합니다. [pyproject.toml#L11](/Users/user/project/autonomos/pyproject.toml#L11)

원하시면 다음 단계로 이어서 해드릴 수 있습니다.
1. `src/autonomos` 내부를 모듈별 책임도로 더 세분화
2. 실제 실행 흐름을 `chat` 기준 시퀀스 다이어그램처럼 정리
3. 구조 개선 포인트만 따로 뽑아서 리팩터링 제안

## Notes
Imported from a real normalized trace.
