# Physical AI Workspace

TradingCodex의 '엄격한 역할 분담 및 안전 통제망'과 Hugging Face LeRobot의 'Physical AI 데이터/모델 파이프라인'을 융합한 로컬 에이전트 프레임워크입니다. 자율주행/로보틱스 제어 알고리즘이 실제 하드웨어(Jetson 등)로 배포되기 전, 가상 환경(ROS2/Isaac Sim)에서 안전하게 검증되도록 워크플로우를 통제합니다.

전체 설계는 [`architecture_plan.md`](./architecture_plan.md), 진행 상황은 [`progress.md`](./progress.md)를 참고하세요.

## 핵심 레이어 (3 Planes)

1. **Workspace Plane** — 에이전트 간 통신 로그, 센서 데이터 스냅샷, 주행 결과, 설정이 저장되는 파일 기반 로컬 메모리 (`workspace_memory/`).
2. **Service Plane** — Django 기반 중앙 통제망. 안전 정책, 제어 명령서, 상태 전이/승인 영수증을 관리하는 로컬 원장(Ledger) (`physical_ai_service/`, `apps/`).
3. **Execution Boundary** — 승인된 명령만 ROS2 토픽으로 발행해 시뮬레이터/실물 로봇으로 전달하는 실행 게이트웨이 (`apps/execution/`).

## 폴더 구조

```text
physical_ai_workspace/
├── manage.py                          # 서비스 진입점 (TradingCodex manage.py 패턴)
├── requirements.txt                   # django>=5.2,<5.3
├── physical_ai_service/               # Service Plane 설정 (TradingCodex의 *_service/ 대응)
│   ├── __init__.py
│   ├── settings.py                    # 로컬 sqlite 원장, 앱 등록, 환경변수 오버라이드
│   ├── urls.py                        # 헬스체크 + /admin/
│   ├── wsgi.py
│   └── asgi.py
├── apps/                              # 역할별 앱 (architecture_plan.md §4 그대로)
│   ├── __init__.py
│   ├── safety/                        # safety-gatekeeper 뼈대
│   │   └── __init__.py / apps.py / models.py / admin.py / migrations/
│   ├── planning/                      # motion-planner 뼈대
│   │   └── (동일 구성)
│   └── execution/                     # execution-operator 뼈대
│       └── (동일 구성)
├── workspace_memory/                  # 파일 기반 메모리 (Ledger DB도 이 아래 생성됨)
│   ├── command_tickets/
│   └── research_logs/
└── references/                        # 외부 참조 코드 (Read-only)
    ├── TradingCodex/
    └── huggingFace_lerobot/
```

## 시작하기

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate --run-syncdb
python manage.py runserver
```

헬스체크: `http://127.0.0.1:8000/` → `{"status": "ok", "service": "physical-ai-service-plane"}`

## 에이전트 역할 (Role Roster)

| 역할 | 설명 |
| --- | --- |
| `head-manager` | 사용자 요청 수신, 워크플로우 분배, 하위 에이전트 산출물 종합 및 승인 상태 관리 |
| `perception-analyst` | 카메라/LiDAR 등 센서 데이터의 품질과 노이즈 상태 평가 |
| `motion-planner` | 전역/지역 경로 최적화 및 조향/가속 논리 작성 (`apps/planning`) |
| `safety-gatekeeper` | 충돌 시간(TTC), 동역학적 한계 검증 및 승인 영수증 발행 (`apps/safety`) |
| `execution-operator` | 최종 승인된 제어 패키지만 시뮬레이터/실물 하드웨어로 전송 (`apps/execution`) |

## 라이선스

[MIT](./LICENSE)
