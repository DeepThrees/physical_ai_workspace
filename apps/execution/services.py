"""execution-operator의 승인된 Command Ticket 발행(Dispatch) 로직.

`apps.safety`가 승인한 Command Ticket만 ExecutionRecord로 남기고
실행 중(EXECUTING) 상태로 전이한다. 실제 ROS2 발행은 이후 Phase에서 연결한다.
"""
from __future__ import annotations

from django.db import transaction

from apps.execution.models import ExecutionRecord
from apps.planning.models import CommandTicket


def dispatch_command_ticket(ticket: CommandTicket) -> ExecutionRecord:
    """승인된 Command Ticket을 실행 원장에 기록하고 EXECUTING으로 전이한다.

    ticket.current_state가 APPROVED가 아니면 ValueError를 발생시킨다.
    ExecutionRecord는 모델 기본 시작 상태(PENDING)로 생성하고,
    ticket_id / receipt_id로 원본 티켓과 승인 영수증을 느슨하게 연결한다.
    실제 ROS2 퍼블리시는 아직 연결하지 않는다.
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

    # TODO: ROS2 Node Publish 로직 추가 예정
    print(
        f"[DUMMY] Dispatch CommandTicket {ticket.ticket_id} "
        f"-> ExecutionRecord {record.pk} (ROS2 publish skipped)"
    )

    return record
