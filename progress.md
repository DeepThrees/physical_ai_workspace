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

## Phase 5 — ROS2 Execution Bridge (근육 연결 완료)

- [X] `apps/execution/services.py` 내에 실제 ROS2 노드(`rclpy`) 연동 구현
  - 장고 방화벽을 통과한 `APPROVED` 상태의 티켓을 읽어 ROS2 제어 명령으로 변환
  - `django_execution_bridge` 임시 노드를 생성하여 `/drive` 토픽으로 `AckermannDriveStamped` 메시지 퍼블리시
  - 시뮬레이터 또는 실제 로봇이 없는 환경에서도 장고(Django) 서버가 뻗지 않도록 `try-except` 임포트 방어 로직 및 에러 핸들링 적용
- [X] Ubuntu 네이티브 환경 연동 및 검증
  - `--system-site-packages` 옵션을 사용한 가상환경(venv) 구성으로 Django와 ROS2 시스템 라이브러리 간 브릿지 환경 구축 완료
  - `rclpy` 임포트 및 초기화 테스트 정상 통과 확인

## Phase 6 — Perception Node (LiDAR 번역기 구현 완료)

- [X] `agents/lidar_translator.py` 인지(Perception) 노드 구현
  - ROS2 `/scan` 토픽을 구독하여 LiDAR 센서 데이터를 실시간 수신 (QoS `sensor_data` 적용)
  - 정면(0도), 좌측(+90도), 우측(-90도) 기준 ±5도 구간의 최솟값을 추출하여 센서 노이즈 및 결측치(`inf`) 완벽 방어
  - 360도 LiDAR의 경계선 인덱스를 부드럽게 잇는 Wrap-around 로직 적용
  - 추출된 거리 데이터를 LLM이 이해할 수 있는 자연어 문장으로 번역하여 `workspace_memory/environment_summary.txt`에 실시간 기록
  - 디스크 I/O 과부하를 막기 위한 2Hz(0.5초) 쓰기 스로틀링(Throttling) 적용 및 실시간 터미널 출력 확인

## Phase 7 — 완전 자율주행 루프(Continuous Loop) 완성 및 한계 도출

- [X] `agents/run_loop.py` 관제탑(Loop) 스크립트 구현
  - 에이전트(`autonomous_agent.py`)와 방화벽(`process_workspace`)을 무한 순차 실행하는 관제탑 구축
  - 하드코딩 프롬프트를 제거하고, LiDAR 번역기가 작성한 `environment_summary.txt`를 동적으로 읽도록 에이전트 리팩토링
  - 파일 읽기 경합(Race Condition) 방지 및 API Rate Limit 회피(1.5초 대기) 로직 적용
- [X] End-to-End 자율주행 E2E 테스트 성공 및 아키텍처 한계(Latency) 확인
  - **[성공]:** 센서(눈) → 번역기 → LLM(뇌) → 장고(방화벽) → ROS2(근육)로 이어지는 100% 자동화 파이프라인 작동 확인
  - **[한계 발견]:** 클라우드 기반 LLM(Gemini)의 네트워크 지연(API 응답 1~2초)과 프로세스 재시동 오버헤드로 인해 최종 제어 주기가 3~4초로 길어짐
  - **[인사이트]:** 실시간 물리 제어(Real-time Control)에서 클라우드 VLM/LLM 단독 구동 시, 반응 지연으로 인한 지그재그 주행(벽 충돌 후 뒤늦은 조향) 등 치명적 한계가 발생함을 직접 확인. (향후 Local SLM(클라우드 API Latency 없는 Small Language Model, PC나 로봇 보드안에서 직접 돌아감) 도입이나 MPC 등 기존 제어 알고리즘과의 하이브리드 아키텍처 연구 필요성 도출)
