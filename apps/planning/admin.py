"""motion-planner Command Ticket 관리자 화면 등록.

참고: references/TradingCodex/apps/orders/admin.py는 OrderTicket 등을
admin.site.register([...])로만 단순 등록하지만, 관리자 화면에서 다수의
Command Ticket을 한눈에 파악하려면 list_display/list_filter/search_fields가
필요하므로 CommandTicket의 필드 구성에 맞게 이를 추가로 구성한다.
"""
from django.contrib import admin

from apps.planning.models import CommandTicket


@admin.register(CommandTicket)
class CommandTicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_id",
        "robot_id",
        "command_type",
        "priority",
        "current_state",
        "mission_id",
        "approval_receipt_id",
        "created_at",
    )
    list_filter = ("command_type", "priority", "current_state", "source")
    search_fields = (
        "ticket_id",
        "robot_id",
        "mission_id",
        "approval_receipt_id",
        "payload_hash",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    readonly_fields = ("created_at", "updated_at")
