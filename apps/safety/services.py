"""safety-gatekeeper의 Command Ticket 검증 및 Approval Receipt 발행 로직.

활성 SafetyPolicy를 CommandTicket 값과 비교해 APPROVED / REJECTED
ApprovalReceipt를 만들고, 원본 티켓의 current_state·approval_receipt_id를 갱신한다.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.planning.models import CommandTicket
from apps.safety.models import ApprovalReceipt, SafetyPolicy

# 물리 환경은 빠르게 변하므로 승인 유효기간을 짧게 둔다.
_RECEIPT_TTL = timedelta(seconds=30)


def evaluate_command_ticket(ticket: CommandTicket) -> ApprovalReceipt:
    """활성 SafetyPolicy로 ticket을 검증하고 ApprovalReceipt를 발행한다.

    위반이 하나라도 있으면 decision=REJECTED, 모두 통과하면 APPROVED.
    마지막으로 ticket.current_state와 approval_receipt_id를 결과에 맞게 갱신한다.
    """
    policies = list(
        SafetyPolicy.objects.filter(active=True).order_by("priority", "policy_id")
    )

    evaluated_policies: list[dict[str, Any]] = []
    evaluated_policy_ids: list[str] = []
    passed_policy_ids: list[str] = []
    failed_policy_ids: list[str] = []
    reasons: list[str] = []
    approved_max_velocity: float | None = None
    approved_max_steering_angle: float | None = None

    for policy in policies:
        if not _policy_applies(policy, ticket):
            continue

        evaluated_policy_ids.append(policy.policy_id)
        policy_reasons = _check_policy_violations(policy, ticket)
        passed = not policy_reasons

        evaluated_policies.append(
            {
                "policy_id": policy.policy_id,
                "passed": passed,
                "reasons": policy_reasons,
            }
        )

        if passed:
            passed_policy_ids.append(policy.policy_id)
            approved_max_velocity = _min_optional(
                approved_max_velocity, policy.max_velocity
            )
            approved_max_steering_angle = _min_optional(
                approved_max_steering_angle, policy.max_steering_angle
            )
        else:
            failed_policy_ids.append(policy.policy_id)
            reasons.extend(policy_reasons)

    decision = (
        ApprovalReceipt.Decision.REJECTED
        if failed_policy_ids
        else ApprovalReceipt.Decision.APPROVED
    )
    receipt_id = _make_receipt_id(ticket)

    with transaction.atomic():
        receipt = ApprovalReceipt.objects.create(
            receipt_id=receipt_id,
            ticket_id=ticket.ticket_id,
            decision=decision,
            evaluated_policy_ids=evaluated_policy_ids,
            passed_policy_ids=passed_policy_ids,
            failed_policy_ids=failed_policy_ids,
            evaluated_policies=evaluated_policies,
            reasons=reasons,
            approved_by="safety-gatekeeper",
            valid=decision == ApprovalReceipt.Decision.APPROVED,
            expires_at=timezone.now() + _RECEIPT_TTL,
            exact_ticket_hash=_ticket_hash(ticket),
            approved_max_velocity=approved_max_velocity,
            approved_max_steering_angle=approved_max_steering_angle,
        )

        if decision == ApprovalReceipt.Decision.APPROVED:
            ticket.current_state = CommandTicket.State.APPROVED
        else:
            ticket.current_state = CommandTicket.State.REJECTED
        ticket.approval_receipt_id = receipt.receipt_id
        ticket.save(update_fields=["current_state", "approval_receipt_id", "updated_at"])

    return receipt


def _policy_applies(policy: SafetyPolicy, ticket: CommandTicket) -> bool:
    """scope·applicable_command_types 기준으로 이 정책이 ticket에 적용되는지 판단."""
    applicable = policy.applicable_command_types or []
    if applicable and ticket.command_type not in applicable:
        return False

    if policy.scope == SafetyPolicy.Scope.GLOBAL:
        return True
    if policy.scope == SafetyPolicy.Scope.ROBOT:
        return bool(policy.scope_target) and policy.scope_target == ticket.robot_id
    if policy.scope == SafetyPolicy.Scope.PLATFORM:
        platform = _context_value(ticket, "platform")
        return bool(policy.scope_target) and policy.scope_target == platform
    return False


def _check_policy_violations(policy: SafetyPolicy, ticket: CommandTicket) -> list[str]:
    """단일 정책 대비 위반 사유 목록. 비어 있으면 통과."""
    reasons: list[str] = []
    pid = policy.policy_id

    if policy.max_velocity is not None:
        if ticket.target_velocity is not None and abs(ticket.target_velocity) > policy.max_velocity:
            reasons.append(
                f"[{pid}] target_velocity={ticket.target_velocity} m/s exceeds "
                f"max_velocity={policy.max_velocity} m/s"
            )
        for idx, waypoint_velocity in _waypoint_velocities(ticket):
            if abs(waypoint_velocity) > policy.max_velocity:
                reasons.append(
                    f"[{pid}] waypoints[{idx}].velocity={waypoint_velocity} m/s exceeds "
                    f"max_velocity={policy.max_velocity} m/s"
                )

    if (
        policy.max_acceleration is not None
        and ticket.target_acceleration is not None
        and abs(ticket.target_acceleration) > policy.max_acceleration
    ):
        reasons.append(
            f"[{pid}] target_acceleration={ticket.target_acceleration} m/s^2 exceeds "
            f"max_acceleration={policy.max_acceleration} m/s^2"
        )

    if (
        policy.max_angular_velocity is not None
        and ticket.target_angular_velocity is not None
        and abs(ticket.target_angular_velocity) > policy.max_angular_velocity
    ):
        reasons.append(
            f"[{pid}] target_angular_velocity={ticket.target_angular_velocity} rad/s "
            f"exceeds max_angular_velocity={policy.max_angular_velocity} rad/s"
        )

    if (
        policy.max_steering_angle is not None
        and ticket.steering_angle is not None
        and abs(ticket.steering_angle) > policy.max_steering_angle
    ):
        reasons.append(
            f"[{pid}] steering_angle={ticket.steering_angle} rad exceeds "
            f"max_steering_angle={policy.max_steering_angle} rad"
        )

    if policy.max_steering_rate is not None:
        steering_rate = _context_float(ticket, "steering_rate")
        if steering_rate is not None and abs(steering_rate) > policy.max_steering_rate:
            reasons.append(
                f"[{pid}] steering_rate={steering_rate} rad/s exceeds "
                f"max_steering_rate={policy.max_steering_rate} rad/s"
            )

    if policy.min_time_to_collision is not None:
        ttc = _context_float(ticket, "time_to_collision")
        if ttc is not None and ttc < policy.min_time_to_collision:
            reasons.append(
                f"[{pid}] time_to_collision={ttc} s is below "
                f"min_time_to_collision={policy.min_time_to_collision} s"
            )

    if policy.min_obstacle_distance is not None:
        distance = _context_float(ticket, "obstacle_distance")
        if distance is not None and distance < policy.min_obstacle_distance:
            reasons.append(
                f"[{pid}] obstacle_distance={distance} m is below "
                f"min_obstacle_distance={policy.min_obstacle_distance} m"
            )

    return reasons


def _waypoint_velocities(ticket: CommandTicket) -> list[tuple[int, float]]:
    """trajectory waypoints에서 (index, velocity) 쌍을 추출한다."""
    results: list[tuple[int, float]] = []
    for idx, waypoint in enumerate(ticket.waypoints or []):
        if not isinstance(waypoint, dict):
            continue
        velocity = waypoint.get("velocity")
        if isinstance(velocity, (int, float)):
            results.append((idx, float(velocity)))
    return results


def _context_value(ticket: CommandTicket, key: str) -> Any:
    """payload → workspace_context 순으로 보조 값을 조회한다."""
    for source in (ticket.payload, ticket.workspace_context):
        if isinstance(source, dict) and key in source:
            return source[key]
    return None


def _context_float(ticket: CommandTicket, key: str) -> float | None:
    value = _context_value(ticket, key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _min_optional(current: float | None, candidate: float | None) -> float | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return min(current, candidate)


def _make_receipt_id(ticket: CommandTicket) -> str:
    return f"apr-{ticket.ticket_id}-{uuid.uuid4().hex[:8]}"


def _ticket_hash(ticket: CommandTicket) -> str:
    """승인 시점의 티켓 내용 해시. payload_hash가 있으면 그대로 사용한다."""
    if ticket.payload_hash:
        return ticket.payload_hash

    snapshot = {
        "ticket_id": ticket.ticket_id,
        "robot_id": ticket.robot_id,
        "command_type": ticket.command_type,
        "target_velocity": ticket.target_velocity,
        "target_angular_velocity": ticket.target_angular_velocity,
        "steering_angle": ticket.steering_angle,
        "target_acceleration": ticket.target_acceleration,
        "waypoints": ticket.waypoints,
        "target_pose": ticket.target_pose,
        "payload": ticket.payload,
    }
    encoded = json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
