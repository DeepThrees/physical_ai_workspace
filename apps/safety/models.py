"""safety-gatekeeper의 Safety Policy / Approval Receipt 모델.

참고: references/TradingCodex/apps/policy/models.py의 PolicyDecision·RestrictedSymbol
패턴과 references/TradingCodex/apps/orders/models.py의 ApprovalReceipt·OrderCheckRun
패턴을, F1TENTH 등 물리 하드웨어의 동역학/충돌 안전 기준에 맞게 이식했다.

흐름: `apps.planning`이 발행한 Command Ticket을 이 앱(`apps.safety`)이
SafetyPolicy 기준으로 검증하고, 그 결과를 ApprovalReceipt로 발행한다.
`apps.execution`은 유효한(APPROVED) Approval Receipt가 있는 Command Ticket만
ROS2 토픽으로 내보낸다. Command Ticket과의 연결은 TradingCodex의
ApprovalReceipt.order_ticket_id와 동일하게, 실제 FK가 아니라 문자열 `ticket_id`로만
느슨하게 매핑한다 (앱 간 결합·마이그레이션 순서 의존성을 피하기 위함이며,
planning/execution 앱의 파일이나 로직은 건드리지 않는다).
"""
from django.db import models


class SafetyPolicy(models.Model):
    """물리 하드웨어(로봇)에 적용되는 안전 정책 기준 한 건.

    F1TENTH 같은 Ackermann 플랫폼과 차동 구동 플랫폼을 모두 포괄할 수 있도록
    속도·조향·가감속·TTC(Time-To-Collision) 관련 한계값을 필드로 두되, 정책마다
    필요한 필드만 채우고 나머지는 비워(None) 둘 수 있다 (예: 조향각 한계는
    Ackermann 플랫폼에만 의미가 있음).
    """

    class Scope(models.TextChoices):
        GLOBAL = "global", "Global (all robots)"
        ROBOT = "robot", "Specific robot"
        PLATFORM = "platform", "Platform class (e.g. ackermann, diff-drive)"

    policy_id = models.CharField(max_length=160, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.GLOBAL)
    # scope=ROBOT일 때는 robot_id, scope=PLATFORM일 때는 플랫폼 식별자를 저장.
    # CommandTicket.robot_id와 동일하게 느슨한 문자열 참조로만 남긴다.
    scope_target = models.CharField(
        max_length=120, blank=True, help_text="scope=robot/platform일 때의 대상 식별자"
    )

    # --- 동역학 한계 ---
    max_velocity = models.FloatField(
        null=True, blank=True, help_text="허용 가능한 최대 선속도 (m/s)"
    )
    max_acceleration = models.FloatField(
        null=True, blank=True, help_text="허용 가능한 최대 가속도 (m/s^2)"
    )
    max_angular_velocity = models.FloatField(
        null=True, blank=True, help_text="허용 가능한 최대 각속도 (rad/s), 차동 구동 계열"
    )
    max_steering_angle = models.FloatField(
        null=True, blank=True, help_text="허용 가능한 최대 조향각 (rad), Ackermann 계열"
    )
    max_steering_rate = models.FloatField(
        null=True, blank=True, help_text="허용 가능한 최대 조향각 변화율 (rad/s)"
    )

    # --- 충돌/근접 안전 한계 ---
    min_time_to_collision = models.FloatField(
        null=True,
        blank=True,
        help_text="최소 TTC(Time-To-Collision, 초). 이보다 낮으면 정책 위반.",
    )
    min_obstacle_distance = models.FloatField(
        null=True, blank=True, help_text="장애물까지 허용되는 최소 거리 (m)"
    )

    # 이 정책이 적용되는 Command Ticket의 종류. planning 앱의
    # CommandTicket.CommandType과 값 체계를 맞추되, 앱 간 결합을 피하기 위해
    # 실제 choices 클래스를 import하지 않고 문자열 목록으로만 느슨하게 둔다.
    applicable_command_types = models.JSONField(
        default=list,
        blank=True,
        help_text='["velocity", "ackermann", "trajectory", ...] 형태, 비어있으면 전체 적용',
    )

    active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(
        default=100, help_text="낮을수록 먼저 평가됨 (정렬용)"
    )

    workspace_context = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "policy_id"]
        verbose_name = "Safety policy"
        verbose_name_plural = "Safety policies"

    def __str__(self) -> str:
        return self.policy_id


class ApprovalReceipt(models.Model):
    """Command Ticket에 대한 Safety Policy 검증 결과 영수증.

    TradingCodex의 ApprovalReceipt/OrderCheckRun과 동일하게, 어떤 정책을
    통과했고 어떤 정책을 위반했는지를 `evaluated_policies`에 정책 단위로
    기록하고, 최종 승인 여부는 `decision`에 담는다. Command Ticket 쪽으로는
    FK가 아니라 `ticket_id` 문자열로만 연결한다.
    """

    class Decision(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    receipt_id = models.CharField(max_length=160, unique=True)
    # apps.planning.CommandTicket.ticket_id를 문자열로만 참조 (FK 아님).
    ticket_id = models.CharField(max_length=160)

    decision = models.CharField(max_length=16, choices=Decision.choices)

    # 이번 검증에 사용된 정책들의 policy_id 목록 (평가 시점 스냅샷).
    evaluated_policy_ids = models.JSONField(default=list, blank=True)
    passed_policy_ids = models.JSONField(default=list, blank=True)
    failed_policy_ids = models.JSONField(default=list, blank=True)
    # 정책별 세부 판정 결과: [{"policy_id", "passed", "reason", ...}, ...]
    evaluated_policies = models.JSONField(default=list, blank=True)
    reasons = models.JSONField(default=list, blank=True)

    approved_by = models.CharField(max_length=128, default="safety-gatekeeper")

    # 물리 환경은 빠르게 변하므로 승인은 짧은 유효기간을 가진다. 유효기간이
    # 지나거나 valid=False가 되면 execution 앱은 이 승인을 신뢰해선 안 된다.
    valid = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # 승인 시점의 Command Ticket 내용에 대한 해시. 승인 이후 티켓 payload가
    # 변경되면 이 해시가 더 이상 일치하지 않으므로 execution 앱이 재검증을
    # 요구할 수 있다 (TradingCodex의 exact_order_hash와 동일한 목적).
    exact_ticket_hash = models.CharField(max_length=64, blank=True)

    # 승인된 실제 한계값 (Command Ticket의 요청값이 정책 한계 내로 클램프된
    # 경우, execution 앱이 참고할 최종 허용치).
    approved_max_velocity = models.FloatField(null=True, blank=True)
    approved_max_steering_angle = models.FloatField(null=True, blank=True)

    workspace_context = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Approval receipt"
        verbose_name_plural = "Approval receipts"

    def __str__(self) -> str:
        return f"{self.decision}: {self.ticket_id}"
