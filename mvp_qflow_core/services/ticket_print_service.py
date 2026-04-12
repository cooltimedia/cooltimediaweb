"""
Ticket print service.

This service centralizes print-flow logging for kiosk/browser-based printing.
It does not attempt to validate physical printer success, because browsers
cannot reliably confirm that level of hardware execution.
"""

from typing import Optional

from django.contrib.auth import get_user_model

from mvp_qflow_core.models import QueueTicket
from mvp_qflow_core.services.log_service import LogService

User = get_user_model()


class TicketPrintService:
    """
    Handles print-related application logging for queue tickets.
    """

    ALLOWED_EVENTS = {
        "print_opened",
        "print_popup_blocked",
        "print_retry_requested",
        "printing_failure",
        "print_cancelled",
        "print_window_closed",
    }

    EVENT_ACTION_MAP = {
        "print_opened": "Print window opened",
        "print_popup_blocked": "Print popup blocked",
        "print_retry_requested": "Print retry requested",
        "printing_failure": "Printing failure",
        "print_cancelled": "Printing cancelled by operator",
        "print_window_closed": "Print window closed",
    }

    @classmethod
    def log_print_event(
        cls,
        *,
        ticket: QueueTicket,
        event: str,
        user: Optional[User] = None,
        payload: Optional[dict] = None,
    ):
        """
        Logs a print-related event for a ticket.

        Args:
            ticket (QueueTicket): Target ticket.
            event (str): One of the allowed print events.
            user (User | None): Optional related user.
            payload (dict | None): Optional structured metadata.

        Returns:
            AppProcessingLog: Created log instance.

        Raises:
            ValueError: If the event is invalid.
        """
        if event not in cls.ALLOWED_EVENTS:
            raise ValueError(f"Unsupported print event: {event}")

        action = cls.EVENT_ACTION_MAP[event]

        if event in {"printing_failure", "print_popup_blocked"}:
            return LogService.error(
                action=action,
                branch=ticket.branch,
                service_type=ticket.service_type,
                ticket=ticket,
                payload=payload or {},
                user=user,
            )

        if event in {"print_cancelled", "print_retry_requested"}:
            return LogService.warning(
                action=action,
                branch=ticket.branch,
                service_type=ticket.service_type,
                ticket=ticket,
                payload=payload or {},
                user=user,
            )

        return LogService.info(
            action=action,
            branch=ticket.branch,
            service_type=ticket.service_type,
            ticket=ticket,
            payload=payload or {},
            user=user,
        )