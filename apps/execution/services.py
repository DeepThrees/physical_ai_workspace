"""execution-operator의 승인된 Command Ticket 발행(Dispatch) 로직.

`apps.safety`가 승인한 Command Ticket만 ExecutionRecord로 남기고
실행 중(EXECUTING) 상태로 전이한 뒤, ROS2 `/drive` 토픽으로
AckermannDriveStamped 제어 명령을 퍼블리시한다.
"""
from __future__ import annotations

from django.db import transaction

from apps.execution.models import ExecutionRecord
from apps.planning.models import CommandTicket

try:
    import rclpy
    from ackermann_msgs.msg import AckermannDriveStamped
except ImportError:
    rclpy = None
    AckermannDriveStamped = None

DRIVE_TOPIC = "/drive"
BRIDGE_NODE_NAME = "django_execution_bridge"
PUBLISHER_QOS_DEPTH = 10


def dispatch_command_ticket(ticket: CommandTicket) -> ExecutionRecord:
    """승인된 Command Ticket을 실행 원장에 기록하고 /drive로 퍼블리시한다.

    ticket.current_state가 APPROVED가 아니면 ValueError를 발생시킨다.
    ExecutionRecord는 모델 기본 시작 상태(PENDING)로 생성하고,
    ticket_id / receipt_id로 원본 티켓과 승인 영수증을 느슨하게 연결한다.
    """
    if ticket.current_state != CommandTicket.State.APPROVED:
        raise ValueError(
            f"CommandTicket {ticket.ticket_id} is not APPROVED "
            f"(current_state={ticket.current_state})"
        )

    with transaction.atomic():
        record = ExecutionRecord.objects.create(
            ticket_id=ticket.ticket_id,
            receipt_id=ticket.approval_receipt_id,
            status=ExecutionRecord.Status.PENDING,
            robot_id=ticket.robot_id,
            workspace_context=ticket.workspace_context or {},
            payload=ticket.payload or {},
            idempotency_key=f"exec-{ticket.ticket_id}",
        )

        ticket.current_state = CommandTicket.State.EXECUTING
        ticket.save(update_fields=["current_state", "updated_at"])

    _publish_ackermann_drive(ticket)
    return record


def _publish_ackermann_drive(ticket: CommandTicket) -> None:
    """ticket.payload의 속도/조향각을 AckermannDriveStamped로 /drive에 발행한다.

    rclpy가 없으면 발행을 건너뛴다. 노드는 발행 후 destroy_node로만 정리하며,
    후속 티켓 처리를 위해 rclpy.shutdown()은 호출하지 않는다.
    """
    if rclpy is None or AckermannDriveStamped is None:
        print(
            "[ROS2] rclpy 또는 ackermann_msgs를 사용할 수 없어 "
            f"/drive 퍼블리시를 건너뜁니다 (ticket={ticket.ticket_id})"
        )
        return

    try:
        if not rclpy.ok():
            rclpy.init(args=None)
    except Exception as exc:
        print(f"[ROS2] rclpy.init failed (ticket={ticket.ticket_id}): {exc}")
        return

    speed, steering_angle = _extract_drive_command(ticket)
    node = None
    try:
        node = rclpy.create_node(BRIDGE_NODE_NAME)
        publisher = node.create_publisher(
            AckermannDriveStamped, DRIVE_TOPIC, PUBLISHER_QOS_DEPTH
        )

        msg = AckermannDriveStamped()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.header.frame_id = ticket.frame_id or "base_link"
        msg.drive.speed = speed
        msg.drive.steering_angle = steering_angle

        publisher.publish(msg)
        print(
            f"[ROS2] Published AckermannDriveStamped to {DRIVE_TOPIC} "
            f"(ticket={ticket.ticket_id}, target_velocity={speed}, "
            f"steering_angle={steering_angle})"
        )
    except Exception as exc:
        print(
            f"[ROS2] Failed to publish ticket {ticket.ticket_id} "
            f"to {DRIVE_TOPIC}: {exc}"
        )
    finally:
        if node is not None:
            node.destroy_node()


def _extract_drive_command(ticket: CommandTicket) -> tuple[float, float]:
    """payload에서 target_velocity/steering_angle을 안전하게 꺼낸다."""
    payload = ticket.payload if isinstance(ticket.payload, dict) else {}
    speed = _safe_float(payload.get("target_velocity"), ticket.target_velocity)
    steering_angle = _safe_float(payload.get("steering_angle"), ticket.steering_angle)
    return speed, steering_angle


def _safe_float(value: object, fallback: object = None) -> float:
    for candidate in (value, fallback):
        if candidate is None:
            continue
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue
    return 0.0
