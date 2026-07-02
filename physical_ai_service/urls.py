"""Phase 1 뼈대 URL 라우팅.

헬스체크와 Django 관리자 화면만 우선 노출한다. 각 Plane의 API 엔드포인트
(Command Ticket 제출, Approval Receipt 조회 등)는 이후 Phase에서 apps/ 하위에
services.py / api.py로 추가된다.
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def health_check(request):
    return JsonResponse({"status": "ok", "service": "physical-ai-service-plane"})


urlpatterns = [
    path("", health_check, name="health-check"),
    path("admin/", admin.site.urls),
]
