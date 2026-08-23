"""workspace_memory/command_tickets JSON을 3단계 파이프라인으로 처리하는 커맨드.

LLM 에이전트가 떨어뜨린 Command Ticket JSON을 읽어
생성(planning) → 검열(safety) → 실행(execution) 순으로 처리한 뒤,
중복 실행을 막기 위해 archive/로 이동한다.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.execution.services import dispatch_command_ticket
from apps.planning.services import create_command_ticket
from apps.safety.models import ApprovalReceipt
from apps.safety.services import evaluate_command_ticket


class Command(BaseCommand):
    help = (
        "workspace_memory/command_tickets/의 JSON 파일을 읽어 "
        "Command Ticket 생성 → 안전 검열 → (승인 시) 실행까지 처리한다."
    )

    def handle(self, *args, **options) -> None:
        tickets_dir = Path(settings.WORKSPACE_MEMORY_DIR) / "command_tickets"
        archive_dir = tickets_dir / "archive"
        tickets_dir.mkdir(parents=True, exist_ok=True)
        archive_dir.mkdir(parents=True, exist_ok=True)

        json_files = sorted(
            path for path in tickets_dir.glob("*.json") if path.is_file()
        )

        self.stdout.write(self.style.NOTICE(f"[inbox] {tickets_dir}"))
        self.stdout.write(self.style.NOTICE(f"[archive] {archive_dir}"))

        if not json_files:
            self.stdout.write(self.style.WARNING("처리할 JSON 파일이 없습니다."))
            return

        self.stdout.write(f"발견된 파일 {len(json_files)}개")

        processed = 0
        failed = 0
        for json_path in json_files:
            if self._process_file(json_path, archive_dir):
                processed += 1
            else:
                failed += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"완료: 처리 {processed}개 / 실패 {failed}개 / 전체 {len(json_files)}개"
            )
        )

    def _process_file(self, json_path: Path, archive_dir: Path) -> bool:
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO(f"=== {json_path.name} ==="))

        try:
            payload = self._load_payload(json_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.stdout.write(self.style.ERROR(f"  [읽기 실패] {exc}"))
            return False

        ticket = None
        try:
            self.stdout.write("  [1/3] Command Ticket 생성 중...")
            ticket = create_command_ticket(**payload)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [1/3] 생성 완료: {ticket.ticket_id} "
                    f"(robot={ticket.robot_id}, type={ticket.command_type}, "
                    f"state={ticket.current_state})"
                )
            )

            self.stdout.write("  [2/3] Safety 검열 중...")
            receipt = evaluate_command_ticket(ticket)
            decision_style = (
                self.style.SUCCESS
                if receipt.decision == ApprovalReceipt.Decision.APPROVED
                else self.style.WARNING
            )
            self.stdout.write(
                decision_style(
                    f"  [2/3] 검열 결과: {receipt.decision} "
                    f"(receipt={receipt.receipt_id})"
                )
            )
            for reason in receipt.reasons or []:
                self.stdout.write(self.style.WARNING(f"         - {reason}"))

            if receipt.decision == ApprovalReceipt.Decision.APPROVED:
                self.stdout.write("  [3/3] 실행(dispatch) 중...")
                record = dispatch_command_ticket(ticket)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [3/3] 실행 기록 생성: ExecutionRecord pk={record.pk} "
                        f"(ticket={ticket.ticket_id}, state={ticket.current_state})"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING("  [3/3] REJECTED — dispatch를 건너뜁니다.")
                )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"  [파이프라인 실패] {exc}"))
            if ticket is not None:
                # 티켓이 이미 만들어졌다면 같은 JSON을 다시 넣지 않도록 보관한다.
                self._archive(json_path, archive_dir)
            return False

        self._archive(json_path, archive_dir)
        return True

    def _load_payload(self, json_path: Path) -> dict:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON 최상위는 object(dict)여야 합니다.")
        return data

    def _archive(self, json_path: Path, archive_dir: Path) -> None:
        destination = archive_dir / json_path.name
        if destination.exists():
            stem = json_path.stem
            suffix = json_path.suffix
            index = 1
            while destination.exists():
                destination = archive_dir / f"{stem}_{index}{suffix}"
                index += 1
        shutil.move(str(json_path), destination)
        self.stdout.write(f"  [archive] {json_path.name} → {destination}")
