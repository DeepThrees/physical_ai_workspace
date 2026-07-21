"""motion-planner의 Command Ticket 생성 로직.

`apps.planning.models.CommandTicket`을 실제로 만들어 DB에 저장하는 지점이다.
여기서 만들어진 티켓은 항상 `State.DRAFT` 상태로 시작하며, 이후 Phase에서
`apps.safety.services.evaluate_command_ticket`이 검증해 승인/거부를 결정한다.
"""
from __future__ import annotations

import uuid
from typing import Any

from apps.planning.models import CommandTicket

# CommandTicket 모델에서 kwargs로 직접 채울 수 있는 필드들.
# ticket_id/current_state/status/robot_id/command_type은 이 함수가 직접
# 관리하므로 제외한다.
_ASSIGNABLE_FIELDS = {
    "mission_id",
    "frame_id",
    "source",
    "target_velocity",
    "target_angular_velocity",
    "steering_angle",
    "target_acceleration",
    "max_velocity_limit",
    "max_duration_ms",
    "waypoints",
    "target_pose",
    "priority",
    "user_visible_summary",
    "created_by",
    "natural_language_source",
    "workspace_context",
    "payload",
}


def create_command_ticket(robot_id: str, command_type: str, **kwargs: Any) -> CommandTicket:
    """새 Command Ticket을 생성해 DB에 저장하고 반환한다.

    kwargs는 CommandTicket의 필드명(target_velocity, steering_angle 등)에
    맞춰 전달하면 그대로 매핑되며, 모델에 정의되지 않은 키는 payload에
    보존한다. 생성된 티켓의 current_state는 항상 State.DRAFT다.

    command_type이 "ackermann"인 경우 target_velocity와 steering_angle이
    모두 주어져야 하며, 하나라도 누락되면 ValueError를 발생시킨다.
    """
    if command_type == CommandTicket.CommandType.ACKERMANN:
        _validate_ackermann_kwargs(kwargs)

    field_values: dict[str, Any] = {}
    extra_payload: dict[str, Any] = {}

    for key, value in kwargs.items():
        if key in _ASSIGNABLE_FIELDS:
            field_values[key] = value
        else:
            extra_payload[key] = value

    if extra_payload:
        payload = dict(field_values.get("payload") or {})
        payload.update(extra_payload)
        field_values["payload"] = payload

    ticket = CommandTicket.objects.create(
        ticket_id=_make_ticket_id(robot_id),
        robot_id=robot_id,
        command_type=command_type,
        current_state=CommandTicket.State.DRAFT,
        status=CommandTicket.State.DRAFT,
        **field_values,
    )
    return ticket


def _validate_ackermann_kwargs(kwargs: dict[str, Any]) -> None:
    """ackermann 명령에 필요한 target_velocity/steering_angle 존재 여부 검사."""
    missing = [
        field
        for field in ("target_velocity", "steering_angle")
        if kwargs.get(field) is None
    ]
    if missing:
        raise ValueError(
            "ackermann command_type requires the following field(s): "
            + ", ".join(missing)
        )


def _make_ticket_id(robot_id: str) -> str:
    return f"cmd-{robot_id}-{uuid.uuid4().hex[:8]}"


def create_straight_drive_ticket(
    robot_id: str, target_velocity: float, duration_ms: int
) -> CommandTicket:
    """steering_angle=0.0으로 고정된 직진 Ackermann 명령 티켓을 생성한다."""
    return create_command_ticket(
        robot_id,
        CommandTicket.CommandType.ACKERMANN,
        target_velocity=target_velocity,
        steering_angle=0.0,
        max_duration_ms=duration_ms,
    )


def create_circular_drive_ticket(
    robot_id: str, target_velocity: float, steering_angle: float, duration_ms: int
) -> CommandTicket:
    """주어진 steering_angle로 회전하는 Ackermann 명령 티켓을 생성한다."""
    return create_command_ticket(
        robot_id,
        CommandTicket.CommandType.ACKERMANN,
        target_velocity=target_velocity,
        steering_angle=steering_angle,
        max_duration_ms=duration_ms,
    )
