# pip install google-genai
"""Gemini API 기반 범용 Physical AI 에이전트.

주변 환경/센서 요약을 분석해 Command Ticket JSON을 생성하고
`workspace_memory/command_tickets/`에 저장한다.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

SYSTEM_PROMPT = (
    "너는 물리 환경(Physical World)에서 작동하는 자율주행 로봇을 제어하는 "
    "AI 에이전트야. 제공되는 주변 환경 및 센서 요약 정보를 분석하여, "
    "충돌을 피하고 안전하게 이동할 수 있도록 목표 속도(0.0~1.0)와 "
    "조향각(-0.5~0.5)을 결정해."
)

ROBOT_ID = "PHYSICAL-AGENT-01"
COMMAND_TYPE = "ackermann"
MAX_DURATION_MS = 1000
MODEL_NAME = "gemini-2.5-flash"

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
    return f"""다음 주변 환경 및 센서 요약을 분석하고, 제어 명령을 JSON으로만 응답해.

환경 요약:
{summary}

반드시 아래 키를 모두 포함해:
- robot_id: "{ROBOT_ID}"
- command_type: "{COMMAND_TYPE}"
- target_velocity: 목표 속도 (float, {VELOCITY_MIN}~{VELOCITY_MAX})
- steering_angle: 조향각 (float, {STEERING_MIN}~{STEERING_MAX}, 좌측 양수 / 우측 음수)
- max_duration_ms: {MAX_DURATION_MS}
- natural_language_source: 현재 환경을 분석하고 왜 이런 제어 결정을 내렸는지 1~2줄 설명
"""


def _require_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "ERROR: GEMINI_API_KEY 환경 변수가 설정되어 있지 않습니다.",
            file=sys.stderr,
        )
        sys.exit(1)
    return api_key


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


def _call_gemini(api_key: str, user_prompt: str) -> dict:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    raw = json.loads(response.text)
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
    api_key = _require_api_key()
    summary = _read_environment_summary()
    user_prompt = _build_user_prompt(summary)
    try:
        ticket = _call_gemini(api_key, user_prompt)
        output_path = _save_ticket(ticket)
    except Exception as exc:
        print(f"ERROR: Command Ticket 생성에 실패했습니다: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"성공: Command Ticket을 저장했습니다 → {output_path}")
    print(json.dumps(ticket, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
