# Progress Log

프로젝트 진행 상황을 시간순으로 기록합니다. 상세 설계는 `architecture_plan.md` 참고.

## Phase 1 — 로컬 서비스 플레인 뼈대 (완료)

**목표:** `architecture_plan.md`의 3-Plane 구조 중 Service Plane을 Django 기반으로 최소 실행 가능한 뼈대로 구축.

**참고한 레퍼런스:** `references/TradingCodex/apps/`, `references/TradingCodex/manage.py`

### 완성된 것
- **`manage.py`**: TradingCodex 패턴을 따른 Django 서비스 진입점.
- **`physical_ai_service/`**: 서비스 설정 패키지 (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`).
  - 로컬 원장(Ledger) DB는 `workspace_memory/ledger.sqlite3`에 생성되도록 설정.
  - `PHYSICAL_AI` 설정 딕셔너리에 `sim_only_mode=True` 기본값으로 시뮬레이터 우선 안전장치 반영.
  - `/` 헬스체크 엔드포인트, `/admin/` 관리자 페이지 라우팅.
- **`apps/`**: 역할별 Django 앱 3종 뼈대 생성 (모델/서비스 로직은 비어있음).
  - `apps/safety` — safety-gatekeeper (Approval Receipt 등은 미구현)
  - `apps/planning` — motion-planner (Command Ticket 등은 미구현)
  - `apps/execution` — execution-operator (ROS2 연동 등은 미구현)
- **`workspace_memory/`**: 파일 기반 메모리 플레인 디렉토리 생성 (`command_tickets/`, `research_logs/`).
- **`requirements.txt`**: `django>=5.2,<5.3`.
- **동작 검증 완료**: `python manage.py check`, `runserver` 부팅 후 헬스체크 응답(`{"status": "ok", ...}`) 정상 확인.
- **GitHub 연동 완료**: `git@github.com:DeepThrees/physical_ai_workspace.git`에 push 완료 (커밋 `d52a67b`).

### 아직 비어있는 것 (Phase 2 대상)
- `apps/safety/models.py` — Safety Policy, Approval Receipt 모델 미정의
- `apps/planning/models.py` — Command Ticket, 경로 계획 모델 미정의
- `apps/execution/models.py` — Execution Result, ROS2 연동 로직 미정의
- 역할별 `services.py`, API 엔드포인트 없음 (현재는 헬스체크만 존재)
- DB 마이그레이션 파일 없음 (모델이 비어있어 아직 생성 불필요)

## Phase 2 — 다음 단계 (예정)

- [X] `apps/safety`: Safety Policy 모델 + TTC/동역학 한계 검증 로직 + Approval Receipt 발행
- [X] `apps/planning`: Command Ticket 모델 + 경로/조향 계획 로직
  - `apps/planning/services.py`에 `create_command_ticket` 핵심 생성 로직 구현 완료 (DRAFT 상태 강제, payload 유연성 확보)
  - 범용적인 조향 제어를 위한 `create_straight_drive_ticket`, `create_circular_drive_ticket` 헬퍼 함수 구현 완료
  - Ackermann 제어 명령 시 필수 파라미터(속도, 조향각) 누락 방지를 위한 유효성 검증 로직 추가
- [X] `apps/execution`: Execution Boundary — 승인된 명령만 ROS2 토픽으로 발행하는 게이트웨이
  - `apps/execution/services.py`에 `dispatch_command_ticket` 핵심 실행 로직 구현 완료
  - APPROVED 상태의 티켓만 ExecutionRecord로 기록하고, 원본 티켓 상태를 EXECUTING으로 안전하게 전이 (트랜잭션 및 멱등성 보장)
  - 로봇 제어 명령 3단계 파이프라인(생성 -> 안전 검열 -> 실행) End-to-End 로컬 테스트 완료
- [X] 앱별 `migrations/` 생성 및 `manage.py migrate` 검증
  - `apps/planning`, `apps/safety`, `apps/execution` 각각 `migrations/0001_initial.py` 생성.
  - 로컬 `workspace_memory/ledger.sqlite3`에 `manage.py migrate` 적용 완료.
  - `manage.py createsuperuser`로 관리자 계정 생성 완료, `/admin/`에서 세 앱 모델(`CommandTicket`, `SafetyPolicy`, `ApprovalReceipt`, `ExecutionRecord`) 조회 가능.
- [X] Django Admin 등록 — `apps/planning/admin.py`, `apps/safety/admin.py`, `apps/execution/admin.py`에 `references/TradingCodex`의 admin 패턴을 참고해 `list_display`/`list_filter`/`search_fields`/`date_hierarchy` 구성.
- [X] Workspace Plane ↔ Service Plane 간 파일 기반 통신 규약 정의 (`workspace_memory/command_tickets/` 포맷)
  - `apps/planning/management/commands/process_workspace.py` 커스텀 커맨드 구현 완료
  - `workspace_memory/command_tickets/` 폴더의 JSON 파일을 읽어 들여 [생성 -> 검열 -> 실행]의 3단계 파이프라인을 자동화 처리하는 로직 완성
  - 중복 실행 방지를 위한 `archive/` 디렉토리 파일 이동 처리 및 에러 핸들링 도입
  - 가상의 LLM JSON 명령서를 활용한 E2E(End-to-End) 파이프라인 통합 테스트 완료

## Phase 3 — Safety Gatekeeper 승인 로직 개발 및 검증 (완료)

- [x] `apps/safety/services.py`에 `evaluate_command_ticket` 핵심 검증 엔진 구현 완료
- [x] 트랜잭션(Transaction) 원자성 확보, 승인 영수증 유효기간(TTL) 설정, 데이터 무결성을 위한 해싱(Hashing) 도입
- [x] 장고 쉘(Django Shell) 및 Admin 웹 화면을 통한 티켓 상태 변환(`DRAFT` -> `REJECTED`) 및 반려 영수증 자동 발행 로컬 테스트 성공

## Phase 4 — Workspace Plane (AI Agent) 연동 (완료)

- [X] `agents/autonomous_agent.py` 독립 에이전트 스크립트 구현
  - 구글 신규 `google-genai` SDK 및 `gemini-2.5-flash` 모델 적용 완료
  - 주변 환경(센서) 텍스트 요약을 바탕으로 목표 속도와 조향각을 추론하는 프롬프트 엔지니어링 적용
  - 모델 응답을 완벽한 JSON(`CommandTicket` 양식)으로 강제 출력하고, 물리적 한계치(`_clamp`) 방어 로직 적용
- [X] End-to-End 파이프라인 통합 테스트 성공
  - AI 에이전트가 생성한 JSON 명령서를 `workspace_memory/command_tickets/` 디렉토리에 비동기 저장
  - Django의 `process_workspace` 커맨드가 이를 읽어 [티켓 생성 -> 방화벽 검열(APPROVED) -> 실행(Dispatch)] 하는 전체 파이프라인 100% 정상 작동 확인
