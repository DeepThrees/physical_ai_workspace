"""Autonomy 관제탑 루프.

매 사이클마다 로컬 Ollama 에이전트와 Django `process_workspace`를
순차 실행한다.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cycle = 1
    while True:
        print(f"=== [Autonomy Cycle #{cycle}] ===", flush=True)
        try:
            subprocess.run(
                [sys.executable, "agents/autonomous_agent.py"],
                check=True,
                cwd=PROJECT_ROOT,
            )
            subprocess.run(
                [sys.executable, "manage.py", "process_workspace"],
                check=True,
                cwd=PROJECT_ROOT,
            )
        except KeyboardInterrupt:
            print("\n관제탑 루프를 종료합니다.")
            sys.exit(0)
        except Exception as exc:
            print(
                f"ERROR: Cycle #{cycle} 실패 — 다음 사이클로 계속합니다: {exc}",
                file=sys.stderr,
            )
        cycle += 1


if __name__ == "__main__":
    main()
