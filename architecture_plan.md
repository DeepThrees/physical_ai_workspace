# Physical AI Agent Framework Architecture (v0.1)

## 1. 시스템 개요 (System Overview)
이 프로젝트는 TradingCodex의 '엄격한 역할 분담 및 안전 통제망'과 Hugging Face LeRobot의 'Physical AI 데이터/모델 파이프라인'을 융합한 로컬 에이전트 프레임워크입니다. 
자율주행 및 로보틱스 제어 알고리즘이 실제 하드웨어(Jetson 등)로 배포되기 전, 가상 환경(ROS2/Isaac Sim)에서 안전하게 검증되도록 워크플로우를 통제합니다.

## 2. 핵심 레이어 (3 Planes)
1. **Workspace Plane (파일 기반 메모리):** 에이전트 간의 통신 로그, 센서 데이터 스냅샷, 주행 결과 마크다운, 설정 파일이 저장되는 로컬 디렉토리.
2. **Service Plane (중앙 통제망):** FastAPI/Django 기반. 안전 정책(Safety Policy), 제어 명령서(Command Ticket), 상태 전이 및 승인 영수증(Approval Receipt)을 관리하는 로컬 원장(Ledger).
3. **Execution Boundary (실행 게이트웨이):** 승인된 명령만 ROS2 토픽(Topic)으로 발행하여 시뮬레이터 또는 실물 로봇(F1TENTH 플랫폼 등)으로 전달하는 엄격한 경계.

## 3. 에이전트 역할 (Role Roster)
* **`head-manager`:** 사용자 요청 수신, 워크플로우 분배, 하위 에이전트 산출물 종합 및 승인 상태 관리.
* **`perception-analyst`:** 카메라/LiDAR 등 센서 데이터의 품질과 노이즈 상태 평가 (LeRobot 파이프라인 참고).
* **`motion-planner`:** 전역/지역 경로 최적화 및 조향/가속 논리(C++/Python) 작성.
* **`safety-gatekeeper`:** 충돌 시간(TTC), 동역학적 한계를 검증하고 이상 없으면 '안전 승인 영수증(Approval Receipt)' 발행 (TradingCodex 리스크 매니저 참고).
* **`execution-operator`:** 최종 승인된 제어 패키지만 시뮬레이터나 실물 하드웨어로 전송.

## 4. 폴더 구조 설계 (Directory Structure)
```text
physical_ai_workspace/
├── architecture_plan.md        # 전체 시스템 설계도 및 컨텍스트 (현재 파일)
├── references/                 # 외부 참조 코드 (에이전트 Read-only)
│   ├── TradingCodex/           # 통제망, MCP, 워크플로우 아키텍처 참고용
│   └── huggingFace_lerobot/    # Vision/Action 모델 데이터 파이프라인 참고용
├── apps/                       # 핵심 서비스 및 에이전트 로직
│   ├── safety/                 # safety-gatekeeper 정책 및 승인 로직
│   ├── planning/               # motion-planner 경로 생성 로직
│   └── execution/              # ROS2 연동 및 하드웨어 배포 경계
├── workspace_memory/           # 에이전트 작업 공간 (파일 기반 메모리)
│   ├── command_tickets/        # 제어 명령서 (JSON)
│   └── research_logs/          # 시뮬레이션 결과 및 분석 로그 (MD)
└── manage.py / main.py         # 로컬 서비스 시작 엔트리포인트