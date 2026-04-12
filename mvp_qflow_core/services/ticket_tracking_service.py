"""
Ticket tracking service.

This service handles customer-facing ticket tracking operations,
especially the flow triggered from QR code access.

Responsibilities:
- Resolve a ticket using its internal token
- Refresh queue snapshot metrics before displaying tracking details
- Build structured tracking data for UI rendering
- Validate and execute customer-initiated ticket cancellation
"""

from dataclasses import dataclass, asdict
from typing import Optional

from django.db import transaction

from mvp_qflow_core.models import QueueTicket, TicketStatus
from mvp_qflow_core.services.log_service import LogService
from mvp_qflow_core.services.queue_metrics_service import QueueMetricsService
from mvp_qflow_core.services.ticket_call_service import TicketCallService


@dataclass
class TicketTrackingData:
    """
    Structured data used by the ticket tracking page.
    """
    ticket_id: int
    ticket_code: str
    internal_token: str
    status: str
    customer_name: Optional[str]
    customer_id: Optional[str]
    is_priority: bool
    people_ahead: int
    estimated_wait_minutes: int
    service_name: str
    service_prefix: str
    branch_name: str
    branch_slug: str
    show_estimated_wait_time: bool
    allow_customer_cancel: bool
    enable_qr_tracking: bool
    public_message: Optional[str]
    secondary_message: Optional[str]
    is_open: bool


class TicketTrackingService:
    """
    Customer-facing service for ticket tracking and self-service cancellation.
    """

    TRACKABLE_STATUSES = {
        TicketStatus.WAITING,
        TicketStatus.CALLED,
        TicketStatus.ATTENDING,
        TicketStatus.FINISHED,
        TicketStatus.MISSED,
        TicketStatus.CANCELLED,
    }

    CUSTOMER_CANCELLABLE_STATUSES = {
        TicketStatus.WAITING,
        TicketStatus.CALLED,
    }

    @classmethod
    def get_ticket_by_token(cls, internal_token: str) -> QueueTicket:
        """
        Returns a ticket by its internal tracking token.

        Args:
            internal_token (str): Unique internal token used in QR tracking.

        Returns:
            QueueTicket: Matching ticket instance.

        Raises:
            ValueError: If the token is empty or invalid.
            QueueTicket.DoesNotExist: If no ticket matches the token.
        """
        normalized_token = cls._normalize_token(internal_token=internal_token)

        return (
            QueueTicket.objects.select_related(
                "branch",
                "service_type",
                "assigned_agent",
            )
            .get(internal_token=normalized_token)
        )

    @classmethod
    def get_tracking_data(
        cls,
        internal_token: str,
        refresh_snapshot: bool = True,
    ) -> TicketTrackingData:
        """
        Resolves a ticket from its token and returns structured tracking data.

        If requested, the ticket snapshot fields are recalculated before
        returning the tracking information.

        Args:
            internal_token (str): Internal tracking token.
            refresh_snapshot (bool): Whether to recalculate queue snapshot data.

        Returns:
            TicketTrackingData: Structured data for UI rendering.
        """
        ticket = cls.get_ticket_by_token(internal_token=internal_token)

        if ticket.status not in cls.TRACKABLE_STATUSES:
            raise ValueError(
                f"Ticket {ticket.ticket_code} is not available for tracking."
            )

        if refresh_snapshot:
            ticket = QueueMetricsService.refresh_ticket_snapshot(ticket=ticket)
            ticket.refresh_from_db()

        cls._log_tracking_access(ticket=ticket)

        return cls._build_tracking_data(ticket=ticket)

    @classmethod
    def can_customer_cancel_ticket(cls, ticket: QueueTicket) -> bool:
        """
        Returns whether the customer is allowed to cancel the ticket.

        Rules:
        - Branch must allow customer cancellation
        - Ticket must be in a cancellable status
        - QR tracking must be enabled for the branch

        Args:
            ticket (QueueTicket): Target ticket.

        Returns:
            bool: True if customer cancellation is allowed.
        """
        cls._validate_ticket_instance(ticket=ticket)

        return all([
            ticket.branch.allow_customer_cancel,
            ticket.branch.enable_qr_tracking,
            ticket.status in cls.CUSTOMER_CANCELLABLE_STATUSES,
        ])

    @classmethod
    def cancel_ticket_by_customer(cls, internal_token: str):
        """
        Cancels a ticket from the customer tracking flow.

        This method:
        - resolves the ticket by internal token
        - validates cancellation permissions
        - delegates cancellation to TicketCallService
        - records the action in the application log

        Args:
            internal_token (str): Internal ticket tracking token.

        Returns:
            TicketActionResult: Result returned by TicketCallService.

        Raises:
            ValueError: If customer cancellation is not allowed.
        """
        with transaction.atomic():
            ticket = cls.get_ticket_by_token(internal_token=internal_token)

            if not cls.can_customer_cancel_ticket(ticket=ticket):
                raise ValueError(
                    f"Ticket {ticket.ticket_code} cannot be cancelled by the customer."
                )

            result = TicketCallService.cancel_ticket(
                ticket=ticket,
                user=None,
                notes="Cancelled from ticket tracking page by customer.",
                cancelled_by_customer=True,
            )

            LogService.warning(
                action="Ticket tracking cancellation executed",
                branch=result.ticket.branch,
                service_type=result.ticket.service_type,
                ticket=result.ticket,
                user=None,
                payload={
                    "ticket_code": result.ticket.ticket_code,
                    "internal_token": result.ticket.internal_token,
                    "status": result.ticket.status,
                    "cancelled_by_customer": True,
                },
            )

            return result

    @classmethod
    def serialize_tracking_data(
        cls,
        internal_token: str,
        refresh_snapshot: bool = True,
    ) -> dict:
        """
        Returns ticket tracking data as a dictionary.

        Useful for JSON responses or template contexts.

        Args:
            internal_token (str): Internal ticket tracking token.
            refresh_snapshot (bool): Whether to refresh queue metrics.

        Returns:
            dict: Serialized tracking data.
        """
        tracking_data = cls.get_tracking_data(
            internal_token=internal_token,
            refresh_snapshot=refresh_snapshot,
        )
        return asdict(tracking_data)

    @classmethod
    def _build_tracking_data(cls, ticket: QueueTicket) -> TicketTrackingData:
        """
        Builds the structured tracking response for a ticket.

        Args:
            ticket (QueueTicket): Target ticket.

        Returns:
            TicketTrackingData: Structured tracking payload.
        """
        show_estimated_wait_time = (
            ticket.branch.show_estimated_wait_time and ticket.status in {
                TicketStatus.WAITING,
                TicketStatus.CALLED,
                TicketStatus.ATTENDING,
            }
        )

        allow_customer_cancel = cls.can_customer_cancel_ticket(ticket=ticket)

        return TicketTrackingData(
            ticket_id=ticket.id,
            ticket_code=ticket.ticket_code,
            internal_token=ticket.internal_token,
            status=ticket.status,
            customer_name=ticket.customer_name,
            customer_id=ticket.customer_id,
            is_priority=ticket.is_priority,
            people_ahead=ticket.people_ahead,
            estimated_wait_minutes=ticket.estimated_wait_minutes,
            service_name=ticket.service_type.name,
            service_prefix=ticket.service_type.prefix,
            branch_name=ticket.branch.name,
            branch_slug=ticket.branch.slug,
            show_estimated_wait_time=show_estimated_wait_time,
            allow_customer_cancel=allow_customer_cancel,
            enable_qr_tracking=ticket.branch.enable_qr_tracking,
            public_message=ticket.branch.public_message,
            secondary_message=ticket.branch.secondary_message,
            is_open=ticket.is_open,
        )

    @classmethod
    def _log_tracking_access(cls, ticket: QueueTicket) -> None:
        """
        Writes an informational log when the tracking page is accessed.

        Args:
            ticket (QueueTicket): Related ticket.
        """
        LogService.info(
            action="Ticket tracking accessed",
            branch=ticket.branch,
            service_type=ticket.service_type,
            ticket=ticket,
            user=None,
            payload={
                "ticket_code": ticket.ticket_code,
                "internal_token": ticket.internal_token,
                "status": ticket.status,
                "people_ahead": ticket.people_ahead,
                "estimated_wait_minutes": ticket.estimated_wait_minutes,
            },
        )

    @staticmethod
    def _normalize_token(internal_token: str) -> str:
        """
        Normalizes and validates the internal token input.

        Args:
            internal_token (str): Raw token input.

        Returns:
            str: Normalized token.

        Raises:
            ValueError: If the token is empty.
        """
        if internal_token is None:
            raise ValueError("internal_token is required.")

        normalized = internal_token.strip()

        if not normalized:
            raise ValueError("internal_token is required.")

        return normalized

    @staticmethod
    def _validate_ticket_instance(ticket: QueueTicket) -> None:
        """
        Validates that the provided object is a saved QueueTicket instance.

        Args:
            ticket (QueueTicket): Target ticket.

        Raises:
            ValueError: If the ticket is invalid.
        """
        if not ticket:
            raise ValueError("ticket is required.")

        if not isinstance(ticket, QueueTicket):
            raise ValueError("ticket must be an instance of QueueTicket.")

        if not ticket.pk:
            raise ValueError("ticket must be a saved QueueTicket instance.")