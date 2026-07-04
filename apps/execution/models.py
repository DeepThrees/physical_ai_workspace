"""execution-operator의 실행 결과(Execution Record) 모델.

참고: references/TradingCodex/apps/orders/models.py의 ExecutionResult 패턴을
ROS2/시뮬레이터로의 실제 발행(Publish) 기록에 맞게 이식했다.

흐름: `apps.planning`이 발행한 Command Ticket을 `apps.safety`가 검증해
Approval Receipt를 발행하면, `apps.execution`(이 앱)은 유효한(APPROVED)
Approval Receipt를 가진 Command Ticket만 실제 ROS2 토픽/시뮬레이터 엔드포인트로
내보낸다. ExecutionRecord는 그 발행 시도와 결과를 남기는 원장(ledger)이다.

Command Ticket / Approval Receipt와의 연결은 실제 FK가 아니라 문자열
`ticket_id` / `receipt_id`로만 느슨하게 매핑한다 (TradingCodex의
ExecutionResult.order_ticket_id / approval_receipt_id와 동일한 목적으로,
앱 간 결합·마이그레이션 순서 의존성을 피하기 위함이며, planning/safety 앱의
파일이나 로직은 건드리지 않는다).
"""
from django.db import models


class ExecutionRecord(models.Model):
    """단일 Command Ticket에 대한 실행(발행) 시도 한 건의 기록.

    승인된 Command Ticket을 실제 ROS2 토픽(`rostopic`)이나 시뮬레이터
    엔드포인트로 발행한 시도/결과를 남긴다. 발행이 실패한 경우
    `error_message`에 사유를 남겨 추후 재시도/원인 분석에 사용한다.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending (발행 대기)"
        PUBLISHED = "PUBLISHED", "Published (발행 완료)"
        FAILED = "FAILED", "Failed (발행 실패)"

    # apps.planning.CommandTicket.ticket_id를 문자열로만 참조 (FK 아님).
    ticket_id = models.CharField(max_length=160)
    # apps.safety.ApprovalReceipt.receipt_id를 문자열로만 참조 (FK 아님).
    receipt_id = models.CharField(max_length=160, blank=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )

    # 동일 티켓이 중복 발행되는 것을 막기 위한 멱등성 키
    # (TradingCodex의 ExecutionResult.idempotency_key와 동일한 목적).
    idempotency_key = models.CharField(
        max_length=220, unique=True, null=True, blank=True
    )

    # 실제 발행 대상: ROS2 토픽 이름(예: /cmd_vel, /ackermann_cmd) 또는
    # 시뮬레이터 엔드포인트 경로.
    target_topic = models.CharField(
        max_length=255,
        blank=True,
        help_text="실제 퍼블리시된 ROS2 토픽 이름 또는 시뮬레이터 엔드포인트 경로 (예: /cmd_vel)",
    )
    # 어떤 어댑터(실물 ROS2 vs 시뮬레이터)를 통해 발행했는지.
    adapter = models.CharField(
        max_length=32,
        default="sim",
        help_text="발행에 사용된 어댑터 (예: sim, ros2)",
    )
    message_type = models.CharField(
        max_length=120,
        blank=True,
        help_text="발행된 ROS2 메시지 타입 (예: geometry_msgs/Twist)",
    )

    robot_id = models.CharField(max_length=120, default="default-robot")

    published_at = models.DateTimeField(null=True, blank=True)

    # 발행 실패 시 사유를 남기는 필드.
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    workspace_context = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Execution record"
        verbose_name_plural = "Execution records"

    def __str__(self) -> str:
        return f"{self.status}: {self.ticket_id}"
