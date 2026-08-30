"""Ollama 로컬 SLM 기반 범용 Physical AI 에이전트.

주변 환경/센서 요약을 분석해 Command Ticket JSON을 생성하고
`workspace_memory/command_tickets/`에 저장한다.
"""
from __future__ import annotations

import json
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SYSTEM_PROMPT = (
    "너는 자율주행 로봇의 제어기야. 주어진 환경 요약을 보고 다음 3가지 규칙 중 하나만 무조건 선택해.\n"
    "🚨 [절대 주행 규칙]\n"
    "1. 전방 > 1.2m: 무조건 직진 (target_velocity: 0.4, steering_angle: 0.0)\n"
    "2. 전방 <= 1.2m 이고 좌측 > 우측: 좌회전 (target_velocity: 0.2, steering_angle: 0.5)\n"
    "3. 전방 <= 1.2m 이고 우측 > 좌측: 우회전 (target_velocity: 0.2, steering_angle: -0.5)"
)

ROBOT_ID = "PHYSICAL-AGENT-01"
COMMAND_TYPE = "ackermann"
MAX_DURATION_MS = 1000
MODEL_NAME = "qwen2.5:3b"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"

VELOCITY_MIN = 0.0
VELOCITY_MAX = 1.0
STEERING_MIN = -0.5
STEERING_MAX = 0.5

SENSOR_WAIT_MESSAGE = "센서 데이터 대기 중..."
SUMMARY_READ_RETRIES = 3
SUMMARY_READ_INTERVAL_SEC = 0.2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TICKETS_DIR = PROJECT_ROOT / "workspace_memory" / "command_tickets"
SUMMARY_PATH = PROJECT_ROOT / "workspace_memory" / "environment_summary.txt"


def _read_environment_summary() -> str:
    """`environment_summary.txt`를 읽고, 없거나 비면 대기 문구를 반환한다."""
    for attempt in range(SUMMARY_READ_RETRIES):
        try:
            text = SUMMARY_PATH.read_text(encoding="utf-8").strip()
        except (FileNotFoundError, OSError):
            text = ""
        if text:
            return text
        if attempt < SUMMARY_READ_RETRIES - 1:
            time.sleep(SUMMARY_READ_INTERVAL_SEC)
    return SENSOR_WAIT_MESSAGE


def _build_user_prompt(summary: str) -> str:
    return f"""다음 센서 요약을 분석하고, 제어 명령을 JSON으로만 응답해.

환경 요약:
{summary}

🚨 환경에 따라 아래 3가지 중 하나의 상태로 응답해:
1. 전방 > 1.2m -> "target_velocity": 0.4, "steering_angle": 0.0
2. 전방 <= 1.2m & 좌측이 더 넓음 -> "target_velocity": 0.2, "steering_angle": 0.5
3. 전방 <= 1.2m & 우측이 더 넓음 -> "target_velocity": 0.2, "steering_angle": -0.5

반드시 "robot_id": "{ROBOT_ID}", "command_type": "{COMMAND_TYPE}", "max_duration_ms": {MAX_DURATION_MS}, "natural_language_source" 키를 모두 포함해서 완벽한 JSON으로 출력해.
"""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _build_command_ticket(raw: dict) -> dict:
    try:
        target_velocity = float(raw["target_velocity"])
        steering_angle = float(raw["steering_angle"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "모델 응답에 유효한 target_velocity / steering_angle이 없습니다."
        ) from exc

    explanation = raw.get("natural_language_source")
    if not isinstance(explanation, str) or not explanation.strip():
        raise ValueError("모델 응답에 natural_language_source 설명이 없습니다.")

    return {
        "robot_id": ROBOT_ID,
        "command_type": COMMAND_TYPE,
        "target_velocity": _clamp(target_velocity, VELOCITY_MIN, VELOCITY_MAX),
        "steering_angle": _clamp(steering_angle, STEERING_MIN, STEERING_MAX),
        "max_duration_ms": MAX_DURATION_MS,
        "natural_language_source": explanation.strip(),
    }


def _call_ollama(user_prompt: str) -> dict:
    payload = {
        "model": MODEL_NAME,
        "prompt": user_prompt,
        "system": SYSTEM_PROMPT,
        "format": "json",
        "stream": False,
    }
    request = urllib.request.Request(
        OLLAMA_GENERATE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Ollama API 호출에 실패했습니다 ({OLLAMA_GENERATE_URL}): {exc}"
        ) from exc

    raw_text = body.get("response") if isinstance(body, dict) else None
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Ollama 응답에 유효한 response 텍스트가 없습니다.")

    raw = json.loads(raw_text)
    if not isinstance(raw, dict):
        raise ValueError("모델 응답 JSON 최상위는 object(dict)여야 합니다.")
    return _build_command_ticket(raw)


def _save_ticket(ticket: dict) -> Path:
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TICKETS_DIR / f"agent_cmd_{secrets.token_hex(4)}.json"
    output_path.write_text(
        json.dumps(ticket, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    summary = _read_environment_summary()
    user_prompt = _build_user_prompt(summary)
    try:
        ticket = _call_ollama(user_prompt)
        output_path = _save_ticket(ticket)
    except Exception as exc:
        print(f"ERROR: Command Ticket 생성에 실패했습니다: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"성공: Command Ticket을 저장했습니다 → {output_path}")
    print(json.dumps(ticket, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
