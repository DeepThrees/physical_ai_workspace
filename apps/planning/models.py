"""motion-planner의 경로/명령 티켓(Command Ticket) 모델.

참고: references/TradingCodex/apps/orders/models.py의 OrderTicket 패턴을
로보틱스/자율주행 제어 명령(F1TENTH 등 Ackermann 플랫폼 및 일반 이동 로봇)에 맞게 이식했다.

Command Ticket은 `motion-planner`가 생성하는 "아직 승인되지 않은" 제어 명령 초안이다.
이후 Phase에서 `apps.safety`가 이 티켓을 검증해 Approval Receipt를 발행하고,
`apps.execution`이 승인된 티켓만 ROS2 토픽으로 발행한다. 이 파일은 그 흐름의
시작점인 Command Ticket 데이터 구조만 정의하며, safety/execution 앱의 파일이나
로직은 건드리지 않는다.
"""
from django.db import models


class CommandTicket(models.Model):
    """단일 제어 명령서.

    Twist(선속도/각속도) 계열과 Ackermann(속도/조향각) 계열 명령을 모두
    표현할 수 있도록 필드를 두되, `command_type`에 따라 어떤 필드 조합이
    유효한지가 결정된다 (예: steering_angle은 Ackermann 플랫폼에서만 사용).
    """

    class CommandType(models.TextChoices):
        VELOCITY = "velocity", "Velocity (Twist: linear + angular)"
        ACKERMANN = "ackermann", "Ackermann drive (velocity + steering angle)"
        TRAJECTORY = "trajectory", "Trajectory (waypoint sequence)"
        STOP = "stop", "Controlled stop"
        EMERGENCY_STOP = "emergency_stop", "Emergency stop (E-STOP)"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        EMERGENCY = "emergency", "Emergency"

    class State(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_SAFETY_REVIEW = "PENDING_SAFETY_REVIEW", "Pending safety review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        EXECUTING = "EXECUTING", "Executing"
        COMPLETED = "COMPLETED", "Completed"
        EXPIRED = "EXPIRED", "Expired"

    ticket_id = models.CharField(max_length=160, unique=True)
    source = models.CharField(max_length=32, default="motion-planner")

    # 어떤 로봇/플랫폼, 어떤 임무(mission)에 대한 명령인지 식별.
    robot_id = models.CharField(max_length=120, default="default-robot")
    mission_id = models.CharField(max_length=120, blank=True)
    frame_id = models.CharField(max_length=64, default="base_link")

    command_type = models.CharField(
        max_length=32, choices=CommandType.choices, default=CommandType.VELOCITY
    )

    # --- Twist 계열 (차동 구동 등 일반 이동 로봇) ---
    target_velocity = models.FloatField(
        null=True, blank=True, help_text="목표 선속도 (m/s)"
    )
    target_angular_velocity = models.FloatField(
        null=True, blank=True, help_text="목표 각속도 (rad/s), 차동 구동 계열 명령"
    )

    # --- Ackermann 계열 (F1TENTH 등 조향식 플랫폼) ---
    steering_angle = models.FloatField(
        null=True, blank=True, help_text="목표 조향각 (rad), Ackermann 계열 명령"
    )

    target_acceleration = models.FloatField(
        null=True, blank=True, help_text="목표 가속도 (m/s^2)"
    )
    max_velocity_limit = models.FloatField(
        null=True, blank=True, help_text="이 명령에 적용되는 최대 속도 한계 (m/s)"
    )
    max_duration_ms = models.PositiveIntegerField(
        null=True, blank=True, help_text="명령 유효 지속 시간 (ms), 초과 시 재계획 필요"
    )

    # --- Trajectory 계열: 경로점 시퀀스 ---
    waypoints = models.JSONField(
        default=list, blank=True, help_text="[{x, y, theta, velocity}, ...] 형태의 경로점 목록"
    )
    target_pose = models.JSONField(
        default=dict, blank=True, help_text="{x, y, theta} 형태의 목표 자세 (선택)"
    )

    priority = models.CharField(
        max_length=16, choices=Priority.choices, default=Priority.NORMAL
    )
    status = models.CharField(max_length=32, default=State.DRAFT)
    current_state = models.CharField(
        max_length=32, choices=State.choices, default=State.DRAFT
    )

    # safety/execution 앱과의 연결점. 다른 앱 모델에 직접 FK를 걸지 않고
    # TradingCodex의 ExecutionResult.approval_receipt_id와 동일하게 느슨한
    # 문자열 참조로만 남겨, 앱 간 결합과 마이그레이션 순서 의존성을 피한다.
    approval_receipt_id = models.CharField(max_length=160, blank=True)

    payload_hash = models.CharField(max_length=64, blank=True)
    user_visible_summary = models.TextField(blank=True)
    created_by = models.CharField(max_length=128, default="motion-planner")
    natural_language_source = models.TextField(blank=True)
    workspace_context = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Command ticket"
        verbose_name_plural = "Command tickets"

    def __str__(self) -> str:
        return self.ticket_id
