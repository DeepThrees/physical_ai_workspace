"""safety-gatekeeper Safety Policy / Approval Receipt 관리자 화면 등록.

참고: references/TradingCodex/apps/policy/admin.py, apps/orders/admin.py는
각 모델을 admin.site.register([...])로만 단순 등록하지만, 어떤 정책이
어떤 티켓을 승인/거부했는지 한눈에 파악하려면 list_display/list_filter/
search_fields가 필요하므로 SafetyPolicy·ApprovalReceipt의 필드 구성에
맞게 이를 추가로 구성한다.
"""
from django.contrib import admin

from apps.safety.models import ApprovalReceipt, SafetyPolicy


@admin.register(SafetyPolicy)
class SafetyPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "policy_id",
        "name",
        "scope",
        "scope_target",
        "active",
        "priority",
        "max_velocity",
        "min_time_to_collision",
        "updated_at",
    )
    list_filter = ("scope", "active")
    search_fields = ("policy_id", "name", "scope_target", "description")
    ordering = ("priority", "policy_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ApprovalReceipt)
class ApprovalReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_id",
        "ticket_id",
        "decision",
        "valid",
        "approved_by",
        "expires_at",
        "created_at",
    )
    list_filter = ("decision", "valid", "approved_by")
    search_fields = ("receipt_id", "ticket_id", "exact_ticket_hash")
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    readonly_fields = ("created_at",)
