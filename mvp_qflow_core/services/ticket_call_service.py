"""
Ticket call service.

This service is responsible for handling operational ticket actions such as:
- calling a ticket
- recalling a ticket
- marking a ticket as missed
- starting service
- finishing service
- cancelling a ticket

It also records call attempt history and writes processing logs for auditing.
"""

from dataclasses import dataclass
from typing import Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from mvp_qflow_core.models import (
    CallEventResult,
    QueueTicket,
    TicketCall,
    TicketStatus,
)
from mvp_qflow_core.services.log_service import LogService

User = get_user_model()


@dataclass
class TicketActionResult:
    """
    Standard result object returned by ticket operational actions.

    This helps the views or APIs consume a predictable response structure.
    """
    success: bool
    ticket: QueueTicket
    message: str
    action: str
    auto_marked_missed: bool = False


class TicketCallService:
    """
    Handles ticket call lifecycle actions.

    Responsibilities:
    - Register call attempts
    - Move tickets to CALLED
    - Mark tickets as MISSED when max attempts is reached
    - Start service on a called ticket
    - Finish service on an attending ticket
    - Cancel active tickets
    """

    OPEN_STATUSES = {
        TicketStatus.WAITING,
        TicketStatus.CALLED,
        TicketStatus.ATTENDING,
    }

    CALLABLE_STATUSES = {
        TicketStatus.WAITING,
        TicketStatus.CALLED,
    }

    @classmethod
    def call_ticket(
        cls,
        ticket: QueueTicket,
        called_by: Optional[User] = None,
        notes: Optional[str] = None,
    ) -> TicketActionResult:
        """
        Calls a ticket or recalls it if it was already called before.

        Behavior:
        - WAITING -> CALLED
        - CALLED -> remains CALLED, increments call attempts
        - if max attempts is reached, the ticket is automatically marked MISSED

        Args:
            ticket (QueueTicket): Target ticket.
            called_by (User | None): User performing the action.
            notes (str | None): Optional notes for the call attempt.

        Returns:
            TicketActionResult: Structured action result.

        Raises:
            ValueError: If the ticket cannot be called.
        """
        cls._validate_ticket_instance(ticket=ticket)

        if ticket.status not in cls.CALLABLE_STATUSES:
            raise ValueError(
                f"Ticket {ticket.ticket_code} cannot be called from status '{ticket.status}'."
            )

        max_attempts = ticket.branch.max_call_attempts

        with transaction.atomic():
            locked_ticket = cls._get_locked_ticket(ticket_id=ticket.id)

            if locked_ticket.status not in cls.CALLABLE_STATUSES:
                raise ValueError(
                    f"Ticket {locked_ticket.ticket_code} cannot be called from status '{locked_ticket.status}'."
                )

            next_attempt_number = locked_ticket.call_attempts + 1

            if next_attempt_number > max_attempts:
                cls._mark_ticket_as_missed(
                    ticket=locked_ticket,
                    user=called_by,
                    notes="Maximum call attempts already exceeded.",
                    result_type=CallEventResult.AUTO_MISSED,
                )
                return TicketActionResult(
                    success=True,
                    ticket=locked_ticket,
                    message="Ticket marked as missed automatically.",
                    action="auto_missed",
                    auto_marked_missed=True,
                )

            locked_ticket.status = TicketStatus.CALLED
            locked_ticket.called_at = timezone.now()
            locked_ticket.call_attempts = next_attempt_number
            locked_ticket.save(
                update_fields=[
                    "status",
                    "called_at",
                    "call_attempts",
                    "updated_at",
                ]
            )

            cls._create_call_event(
                ticket=locked_ticket,
                attempt_number=next_attempt_number,
                result=CallEventResult.CALLED,
                called_by=called_by,
                notes=notes,
            )

            LogService.info(
                action="Ticket called",
                branch=locked_ticket.branch,
                service_type=locked_ticket.service_type,
                ticket=locked_ticket,
                user=called_by,
                payload={
                    "ticket_code": locked_ticket.ticket_code,
                    "attempt_number": next_attempt_number,
                    "status": locked_ticket.status,
                    "max_call_attempts": max_attempts,
                    "called_at": locked_ticket.called_at.isoformat() if locked_ticket.called_at else None,
                    "notes": notes,
                },
            )

            auto_marked_missed = False
            message = f"Ticket {locked_ticket.ticket_code} called successfully."

            if locked_ticket.call_attempts >= max_attempts:
                message += " Maximum attempts reached on this call. Next no-response should mark it as missed."

            return TicketActionResult(
                success=True,
                ticket=locked_ticket,
                message=message,
                action="called",
                auto_marked_missed=auto_marked_missed,
            )

    @classmethod
    def mark_no_response(
        cls,
        ticket: QueueTicket,
        user: Optional[User] = None,
        notes: Optional[str] = None,
    ) -> TicketActionResult:
        """
        Marks a ticket call as having no customer response.

        If the current number of attempts has reached the configured branch limit,
        the ticket is automatically marked as MISSED.

        Typical usage:
        - call the ticket
        - wait the configured interval in the UI/workflow
        - if no one responds, call this method

        Args:
            ticket (QueueTicket): Target ticket.
            user (User | None): User performing the action.
            notes (str | None): Optional notes.

        Returns:
            TicketActionResult: Structured action result.

        Raises:
            ValueError: If the action is not valid for the current ticket status.
        """
        cls._validate_ticket_instance(ticket=ticket)

        if ticket.status != TicketStatus.CALLED:
            raise ValueError(
                f"Ticket {ticket.ticket_code} can only be marked as no response from status 'called'."
            )

        with transaction.atomic():
            locked_ticket = cls._get_locked_ticket(ticket_id=ticket.id)

            if locked_ticket.status != TicketStatus.CALLED:
                raise ValueError(
                    f"Ticket {locked_ticket.ticket_code} can only be marked as no response from status 'called'."
                )

            cls._create_call_event(
                ticket=locked_ticket,
                attempt_number=locked_ticket.call_attempts,
                result=CallEventResult.NO_RESPONSE,
                called_by=user,
                notes=notes,
            )

            max_attempts = locked_ticket.branch.max_call_attempts

            if locked_ticket.call_attempts >= max_attempts:
                cls._mark_ticket_as_missed(
                    ticket=locked_ticket,
                    user=user,
                    notes=notes or "Customer did not respond after maximum call attempts.",
                    result_type=CallEventResult.AUTO_MISSED,
                )
                return TicketActionResult(
                    success=True,
                    ticket=locked_ticket,
                    message="Ticket marked as missed after no response.",
                    action="auto_missed",
                    auto_marked_missed=True,
                )

            LogService.warning(
                action="Ticket no response recorded",
                branch=locked_ticket.branch,
                service_type=locked_ticket.service_type,
                ticket=locked_ticket,
                user=user,
                payload={
                    "ticket_code": locked_ticket.ticket_code,
                    "attempt_number": locked_ticket.call_attempts,
                    "status": locked_ticket.status,
                    "max_call_attempts": max_attempts,
                    "notes": notes,
                },
            )

            return TicketActionResult(
                success=True,
                ticket=locked_ticket,
                message="No response recorded for the current call attempt.",
                action="no_response",
                auto_marked_missed=False,
            )

    @classmethod
    def start_service(
        cls,
        ticket: QueueTicket,
        user: Optional[User] = None,
        notes: Optional[str] = None,
    ) -> TicketActionResult:
        """
        Moves a ticket from CALLED to ATTENDING.

        Also records the assigned staff member when provided.

        Args:
            ticket (QueueTicket): Target ticket.
            user (User | None): Staff member starting the service.
            notes (str | None): Optional notes.

        Returns:
            TicketActionResult: Structured action result.

        Raises:
            ValueError: If the ticket is not in a valid status.
        """
        cls._validate_ticket_instance(ticket=ticket)

        if ticket.status != TicketStatus.CALLED:
            raise ValueError(
                f"Ticket {ticket.ticket_code} can only start service from status 'called'."
            )

        with transaction.atomic():
            locked_ticket = cls._get_locked_ticket(ticket_id=ticket.id)

            if locked_ticket.status != TicketStatus.CALLED:
                raise ValueError(
                    f"Ticket {locked_ticket.ticket_code} can only start service from status 'called'."
                )

            locked_ticket.status = TicketStatus.ATTENDING
            locked_ticket.service_start_at = timezone.now()

            if user:
                locked_ticket.assigned_agent = user

            locked_ticket.save(
                update_fields=[
                    "status",
                    "service_start_at",
                    "assigned_agent",
                    "updated_at",
                ]
            )

            cls._create_call_event(
                ticket=locked_ticket,
                attempt_number=locked_ticket.call_attempts or 1,
                result=CallEventResult.ANSWERED,
                called_by=user,
                notes=notes,
            )

            LogService.info(
                action="Service started",
                branch=locked_ticket.branch,
                service_type=locked_ticket.service_type,
                ticket=locked_ticket,
                user=user,
                payload={
                    "ticket_code": locked_ticket.ticket_code,
                    "status": locked_ticket.status,
                    "service_start_at": locked_ticket.service_start_at.isoformat()
                    if locked_ticket.service_start_at else None,
                    "assigned_agent_id": locked_ticket.assigned_agent_id,
                    "notes": notes,
                },
            )

            return TicketActionResult(
                success=True,
                ticket=locked_ticket,
                message=f"Service started for ticket {locked_ticket.ticket_code}.",
                action="start_service",
                auto_marked_missed=False,
            )

    @classmethod
    def finish_service(
        cls,
        ticket: QueueTicket,
        user: Optional[User] = None,
        notes: Optional[str] = None,
    ) -> TicketActionResult:
        """
        Moves a ticket from ATTENDING to FINISHED.

        Args:
            ticket (QueueTicket): Target ticket.
            user (User | None): User performing the action.
            notes (str | None): Optional notes.

        Returns:
            TicketActionResult: Structured action result.

        Raises:
            ValueError: If the ticket is not in ATTENDING status.
        """
        cls._validate_ticket_instance(ticket=ticket)

        if ticket.status != TicketStatus.ATTENDING:
            raise ValueError(
                f"Ticket {ticket.ticket_code} can only be finished from status 'attending'."
            )

        with transaction.atomic():
            locked_ticket = cls._get_locked_ticket(ticket_id=ticket.id)

            if locked_ticket.status != TicketStatus.ATTENDING:
                raise ValueError(
                    f"Ticket {locked_ticket.ticket_code} can only be finished from status 'attending'."
                )

            locked_ticket.status = TicketStatus.FINISHED
            locked_ticket.finished_at = timezone.now()

            if user and not locked_ticket.assigned_agent_id:
                locked_ticket.assigned_agent = user

            locked_ticket.save(
                update_fields=[
                    "status",
                    "finished_at",
                    "assigned_agent",
                    "updated_at",
                ]
            )

            LogService.info(
                action="Service finished",
                branch=locked_ticket.branch,
                service_type=locked_ticket.service_type,
                ticket=locked_ticket,
                user=user,
                payload={
                    "ticket_code": locked_ticket.ticket_code,
                    "status": locked_ticket.status,
                    "finished_at": locked_ticket.finished_at.isoformat()
                    if locked_ticket.finished_at else None,
                    "assigned_agent_id": locked_ticket.assigned_agent_id,
                    "notes": notes,
                },
            )

            return TicketActionResult(
                success=True,
                ticket=locked_ticket,
                message=f"Ticket {locked_ticket.ticket_code} marked as finished.",
                action="finish_service",
                auto_marked_missed=False,
            )

    @classmethod
    def cancel_ticket(
        cls,
        ticket: QueueTicket,
        user: Optional[User] = None,
        notes: Optional[str] = None,
        cancelled_by_customer: bool = False,
    ) -> TicketActionResult:
        """
        Cancels an active ticket.

        This can be used from:
        - staff dashboard
        - tracking page when customer cancellation is allowed

        Args:
            ticket (QueueTicket): Target ticket.
            user (User | None): Optional authenticated user.
            notes (str | None): Optional reason or note.
            cancelled_by_customer (bool): Whether cancellation came from customer flow.

        Returns:
            TicketActionResult: Structured action result.

        Raises:
            ValueError: If the ticket is already closed.
        """
        cls._validate_ticket_instance(ticket=ticket)

        if ticket.status not in cls.OPEN_STATUSES:
            raise ValueError(
                f"Ticket {ticket.ticket_code} cannot be cancelled from status '{ticket.status}'."
            )

        with transaction.atomic():
            locked_ticket = cls._get_locked_ticket(ticket_id=ticket.id)

            if locked_ticket.status not in cls.OPEN_STATUSES:
                raise ValueError(
                    f"Ticket {locked_ticket.ticket_code} cannot be cancelled from status '{locked_ticket.status}'."
                )

            locked_ticket.status = TicketStatus.CANCELLED
            locked_ticket.cancelled_at = timezone.now()
            locked_ticket.save(
                update_fields=[
                    "status",
                    "cancelled_at",
                    "updated_at",
                ]
            )

            action_name = (
                "Ticket cancelled by customer"
                if cancelled_by_customer
                else "Ticket cancelled"
            )

            LogService.warning(
                action=action_name,
                branch=locked_ticket.branch,
                service_type=locked_ticket.service_type,
                ticket=locked_ticket,
                user=user,
                payload={
                    "ticket_code": locked_ticket.ticket_code,
                    "status": locked_ticket.status,
                    "cancelled_at": locked_ticket.cancelled_at.isoformat()
                    if locked_ticket.cancelled_at else None,
                    "cancelled_by_customer": cancelled_by_customer,
                    "notes": notes,
                },
            )

            return TicketActionResult(
                success=True,
                ticket=locked_ticket,
                message=f"Ticket {locked_ticket.ticket_code} cancelled successfully.",
                action="cancel_ticket",
                auto_marked_missed=False,
            )

    @classmethod
    def mark_missed_manually(
        cls,
        ticket: QueueTicket,
        user: Optional[User] = None,
        notes: Optional[str] = None,
    ) -> TicketActionResult:
        """
        Marks a ticket as MISSED manually.

        This is useful when the operator decides to close the turn
        without waiting for the automatic cycle to finish.

        Args:
            ticket (QueueTicket): Target ticket.
            user (User | None): User performing the action.
            notes (str | None): Optional notes.

        Returns:
            TicketActionResult: Structured action result.
        """
        cls._validate_ticket_instance(ticket=ticket)

        if ticket.status not in cls.CALLABLE_STATUSES:
            raise ValueError(
                f"Ticket {ticket.ticket_code} cannot be marked as missed from status '{ticket.status}'."
            )

        with transaction.atomic():
            locked_ticket = cls._get_locked_ticket(ticket_id=ticket.id)

            if locked_ticket.status not in cls.CALLABLE_STATUSES:
                raise ValueError(
                    f"Ticket {locked_ticket.ticket_code} cannot be marked as missed from status '{locked_ticket.status}'."
                )

            cls._mark_ticket_as_missed(
                ticket=locked_ticket,
                user=user,
                notes=notes or "Ticket marked as missed manually.",
                result_type=CallEventResult.MANUAL_MISSED,
            )

            return TicketActionResult(
                success=True,
                ticket=locked_ticket,
                message=f"Ticket {locked_ticket.ticket_code} marked as missed.",
                action="mark_missed",
                auto_marked_missed=True,
            )

    @classmethod
    def _mark_ticket_as_missed(
        cls,
        ticket: QueueTicket,
        user: Optional[User] = None,
        notes: Optional[str] = None,
        result_type: str = CallEventResult.AUTO_MISSED,
    ) -> None:
        """
        Internal helper that marks the ticket as MISSED and logs the action.

        Args:
            ticket (QueueTicket): Locked ticket instance.
            user (User | None): Related user.
            notes (str | None): Optional notes.
            result_type (str): Call event result type.
        """
        ticket.status = TicketStatus.MISSED
        ticket.missed_at = timezone.now()
        ticket.save(
            update_fields=[
                "status",
                "missed_at",
                "updated_at",
            ]
        )

        cls._create_call_event(
            ticket=ticket,
            attempt_number=ticket.call_attempts or 1,
            result=result_type,
            called_by=user,
            notes=notes,
        )

        LogService.warning(
            action="Ticket marked as missed",
            branch=ticket.branch,
            service_type=ticket.service_type,
            ticket=ticket,
            user=user,
            payload={
                "ticket_code": ticket.ticket_code,
                "status": ticket.status,
                "call_attempts": ticket.call_attempts,
                "max_call_attempts": ticket.branch.max_call_attempts,
                "missed_at": ticket.missed_at.isoformat() if ticket.missed_at else None,
                "notes": notes,
            },
        )

    @staticmethod
    def _create_call_event(
        ticket: QueueTicket,
        attempt_number: int,
        result: str,
        called_by: Optional[User] = None,
        notes: Optional[str] = None,
    ) -> TicketCall:
        """
        Creates a TicketCall history record.

        Args:
            ticket (QueueTicket): Related ticket.
            attempt_number (int): Attempt number.
            result (str): One of CallEventResult values.
            called_by (User | None): Operator.
            notes (str | None): Optional notes.

        Returns:
            TicketCall: Created call event.
        """
        return TicketCall.objects.create(
            ticket=ticket,
            attempt_number=attempt_number,
            result=result,
            called_by=called_by,
            notes=notes,
        )

    @staticmethod
    def _validate_ticket_instance(ticket: QueueTicket) -> None:
        """
        Validates that the provided object is a usable QueueTicket instance.
        """
        if not ticket:
            raise ValueError("ticket is required.")

        if not isinstance(ticket, QueueTicket):
            raise ValueError("ticket must be an instance of QueueTicket.")

        if not ticket.pk:
            raise ValueError("ticket must be a saved QueueTicket instance.")

    @staticmethod
    def _get_locked_ticket(ticket_id: int) -> QueueTicket:
        """
        Fetches and locks a ticket row for safe updates inside a transaction.

        Args:
            ticket_id (int): Ticket primary key.

        Returns:
            QueueTicket: Locked ticket instance.
        """
        return (
            QueueTicket.objects.select_for_update()
            .select_related("branch","service_type")
            .get(pk=ticket_id)
        )
        """
        return QueueTicket.objects.select_for_update().select_related(
            "branch",
            "service_type",
            "assigned_agent",
        ).get(pk=ticket_id)
        """
    