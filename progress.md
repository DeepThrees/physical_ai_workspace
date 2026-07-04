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

- [ ] `apps/safety`: Safety Policy 모델 + TTC/동역학 한계 검증 로직 + Approval Receipt 발행
- [X] `apps/planning`: Command Ticket 모델 + 경로/조향 계획 로직
- [ ] `apps/execution`: Execution Boundary — 승인된 명령만 ROS2 토픽으로 발행하는 게이트웨이
- [ ] 앱별 `migrations/` 생성 및 `manage.py migrate` 검증
- [ ] Workspace Plane ↔ Service Plane 간 파일 기반 통신 규약 정의 (`workspace_memory/command_tickets/` 포맷)
