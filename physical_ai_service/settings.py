"""Physical AI Service Plane 기본 설정 (Phase 1 뼈대).

TradingCodex의 settings.py 패턴을 참고: 환경변수로 오버라이드 가능한 로컬 우선
설정을 사용하고, 로컬 원장(Ledger)은 workspace_memory/ 아래 sqlite3 파일로 둔다.
"""
from __future__ import annotations

import os
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent
BASE_DIR = SERVICE_DIR.parent
WORKSPACE_MEMORY_DIR = BASE_DIR / "workspace_memory"


def default_db_path() -> str:
    configured = os.environ.get("PHYSICAL_AI_DB_NAME")
    if configured:
        path = Path(configured).expanduser().resolve()
    else:
        path = WORKSPACE_MEMORY_DIR / "ledger.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


SECRET_KEY = os.environ.get("PHYSICAL_AI_SECRET_KEY", "physical-ai-local-dev-key")
DEBUG = os.environ.get("PHYSICAL_AI_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("PHYSICAL_AI_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

ROOT_URLCONF = "physical_ai_service.urls"
WSGI_APPLICATION = "physical_ai_service.wsgi.application"
ASGI_APPLICATION = "physical_ai_service.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Phase 1 뼈대: 역할별 앱 골격만 등록. 모델/서비스 로직은 이후 Phase에서 채운다.
    "apps.safety",
    "apps.planning",
    "apps.execution",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": default_db_path(),
        "OPTIONS": {"timeout": int(os.environ.get("PHYSICAL_AI_SQLITE_TIMEOUT", "30"))},
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# Phase 1 뼈대용 안전/실행 관련 전역 설정. 세부 정책은 apps.safety에서 확장한다.
PHYSICAL_AI = {
    "sim_only_mode": os.environ.get("PHYSICAL_AI_SIM_ONLY", "1") == "1",
    "allowed_execution_targets": ["isaac-sim", "ros2-sim"],
    "enable_hardware_execution": False,
}
