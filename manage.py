#!/usr/bin/env python3
"""Physical AI Service Plane - 로컬 통제망 커맨드라인 진입점.

TradingCodex의 manage.py 패턴을 참고하여, 이 스크립트는 안전 정책(Safety Policy),
경로 계획(Motion Planning), 실행 게이트웨이(Execution Boundary) 앱을 하나의
Django 서비스로 구동한다.
"""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physical_ai_service.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django를 임포트할 수 없습니다. 가상환경을 활성화하고 "
            "`pip install -r requirements.txt`를 실행했는지 확인하세요."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
