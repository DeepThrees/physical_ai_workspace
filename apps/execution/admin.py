"""execution-operator Execution Record 관리자 화면 등록.

참고: references/TradingCodex/apps/orders/admin.py는 ExecutionResult 등을
admin.site.register([...])로만 단순 등록하지만, 어떤 티켓이 실제로 어떤
토픽/어댑터로 발행되었고 성공/실패했는지 한눈에 파악하려면
list_display/list_filter/search_fields가 필요하므로 ExecutionRecord의
필드 구성에 맞게 이를 추가로 구성한다.
"""
from django.contrib import admin

from apps.execution.models import ExecutionRecord


@admin.register(ExecutionRecord)
class ExecutionRecordAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_id",
        "receipt_id",
        "status",
        "robot_id",
        "target_topic",
        "adapter",
        "retry_count",
        "published_at",
        "created_at",
    )
    list_filter = ("status", "adapter", "robot_id")
    search_fields = ("ticket_id", "receipt_id", "idempotency_key", "target_topic")
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    readonly_fields = ("created_at", "updated_at")
