"""
Ticket creation service.

This service is responsible for creating queue tickets using the configured
branch and service rules, generating stable identifiers, and recording
initial queue metrics.
"""

import time
import uuid
from dataclasses import dataclass
from typing import Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from mvp_qflow_core.models import (
    AppProcessingLog,
    BranchSetting,
    LogLevel,
    QueueTicket,
    ServiceType,
    TicketStatus,
)
from mvp_qflow_core.services.ticket_sequence_service import TicketSequenceService
from mvp_qflow_core.services.log_service import LogService

User = get_user_model()


@dataclass
class TicketCreationData:
    """
    Input payload for ticket creation.

    This dataclass helps keep the service API clean and explicit.
    """
    branch: BranchSetting
    service_type: ServiceType
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    is_priority: bool = False
    created_by: Optional[User] = None


class TicketCreationService:
    """
    Handles the full ticket creation workflow.

    Responsibilities:
    - Validate branch/service consistency
    - Generate the next ticket number
    - Build user-facing and internal identifiers
    - Compute queue snapshot metrics
    - Create the QueueTicket
    - Register initial processing logs
    """

    @classmethod
    def create_ticket(cls, data: TicketCreationData) -> QueueTicket:
        """
        Creates a new queue ticket.

        Args:
            data (TicketCreationData): Structured input required
                to build the ticket.

        Returns:
            QueueTicket: The newly created ticket instance.
        """
        cls._validate_creation_data(data=data)

        with transaction.atomic():
            next_number = TicketSequenceService.get_next_number(
                service_type=data.service_type
            )

            people_ahead = cls._calculate_people_ahead(
                branch=data.branch,
                service_type=data.service_type,
                is_priority=data.is_priority,
            )

            estimated_wait_minutes = cls._calculate_estimated_wait_minutes(
                service_type=data.service_type,
                people_ahead=people_ahead,
            )

            ticket_code = cls._build_ticket_code(
                service_type=data.service_type,
                number=next_number,
            )

            internal_token = cls._build_internal_token(
                branch=data.branch,
                service_type=data.service_type,
            )

            ticket = QueueTicket.objects.create(
                branch=data.branch,
                service_type=data.service_type,
                number=next_number,
                ticket_code=ticket_code,
                internal_token=internal_token,
                customer_name=cls._normalize_optional_string(data.customer_name),
                customer_id=cls._normalize_optional_string(data.customer_id),
                is_priority=cls._resolve_priority_flag(
                    branch=data.branch,
                    requested_priority=data.is_priority,
                ),
                people_ahead=people_ahead,
                estimated_wait_minutes=estimated_wait_minutes,
                status=TicketStatus.WAITING,
            )

            cls._log_ticket_created(
                ticket=ticket,
                user=data.created_by,
            )

            return ticket

    @classmethod
    def _validate_creation_data(cls, data: TicketCreationData) -> None:
        """
        Validates the ticket creation request.

        Raises:
            ValueError: If the data is invalid.
        """
        if not data.branch:
            raise ValueError("branch is required.")

        if not data.service_type:
            raise ValueError("service_type is required.")

        if data.service_type.branch_id != data.branch.id:
            raise ValueError("service_type does not belong to the given branch.")

        if not data.branch.is_active:
            raise ValueError("The selected branch is inactive.")

        if not data.service_type.is_active:
            raise ValueError("The selected service is inactive.")

        if data.branch.requires_identification and not data.customer_id:
            raise ValueError("customer_id is required for this branch.")

    @classmethod
    def _calculate_people_ahead(
        cls,
        branch: BranchSetting,
        service_type: ServiceType,
        is_priority: bool,
    ) -> int:
        """
        Calculates how many open tickets are ahead of the new ticket.

        For the MVP, the rule is intentionally simple and predictable:

        - If the branch has a priority lane and the new ticket is priority,
          only priority open tickets in the same service are counted ahead.
        - Otherwise, all open waiting/called/attending tickets in the same
          service are counted ahead.

        Args:
            branch (BranchSetting): The branch being used.
            service_type (ServiceType): The selected service.
            is_priority (bool): Whether the new ticket is priority.

        Returns:
            int: Number of tickets ahead in queue.
        """
        open_statuses = [
            TicketStatus.WAITING,
            TicketStatus.CALLED,
            TicketStatus.ATTENDING,
        ]

        queryset = QueueTicket.objects.filter(
            branch=branch,
            service_type=service_type,
            status__in=open_statuses,
        )

        if branch.has_priority_lane and is_priority:
            queryset = queryset.filter(is_priority=True)

        return queryset.count()

    @classmethod
    def _calculate_estimated_wait_minutes(
        cls,
        service_type: ServiceType,
        people_ahead: int,
    ) -> int:
        """
        Estimates queue wait time in minutes.

        This MVP formula is intentionally simple:
            estimated_wait = people_ahead * average_service_time_minutes

        Args:
            service_type (ServiceType): The selected service.
            people_ahead (int): Number of active tickets ahead.

        Returns:
            int: Estimated waiting time in minutes.
        """
        average_service_time = service_type.average_service_time_minutes or 0
        return people_ahead * average_service_time

    @classmethod
    def _build_ticket_code(cls, service_type: ServiceType, number: int) -> str:
        """
        Builds the human-readable ticket code.

        Example:
            A-001
            CA-014
            LAB-203

        Args:
            service_type (ServiceType): The service owning the prefix.
            number (int): The sequential ticket number.

        Returns:
            str: Human-readable ticket code.
        """
        return f"{service_type.prefix}-{number:03d}"

    @classmethod
    def _build_internal_token(
        cls,
        branch: BranchSetting,
        service_type: ServiceType,
    ) -> str:
        """
        Builds a collision-resistant internal token used for QR tracking.

        Structure example:
            b3-s8-1743601123456-a1b2c3

        Components:
        - branch id
        - service id
        - current timestamp in milliseconds
        - short UUID fragment

        Args:
            branch (BranchSetting): Related branch.
            service_type (ServiceType): Related service.

        Returns:
            str: Unique internal token.
        """
        milliseconds = int(time.time() * 1000)
        short_uuid = uuid.uuid4().hex[:6]
        return f"b{branch.id}-s{service_type.id}-{milliseconds}-{short_uuid}"

    @staticmethod
    def _normalize_optional_string(value: Optional[str]) -> Optional[str]:
        """
        Trims optional string values and converts empty strings to None.

        Args:
            value (str | None): Input string.

        Returns:
            str | None: Normalized value.
        """
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _resolve_priority_flag(
        branch: BranchSetting,
        requested_priority: bool,
    ) -> bool:
        """
        Resolves whether the ticket should be stored as priority.

        Even if the branch does not have a dedicated priority lane,
        the system may still store the ticket as priority so that
        operational rules can prioritize it later.

        Args:
            branch (BranchSetting): Related branch.
            requested_priority (bool): Requested priority state.

        Returns:
            bool: Final priority flag.
        """
        return bool(requested_priority and branch.has_priority_lane) or bool(
            requested_priority and not branch.has_priority_lane
        )

    @classmethod
    def _log_ticket_created(
        cls,
        ticket: QueueTicket,
        user: Optional[User] = None,
    ) -> None:
        """
        Writes the initial application log after ticket creation.

        Args:
            ticket (QueueTicket): The created ticket.
            user (User | None): Optional user who initiated the process.
        """
        LogService.info(
            action="Ticket created",
            branch=ticket.branch,
            service_type=ticket.service_type,
            ticket=ticket,
            payload={
                "ticket_code": ticket.ticket_code,
                "number": ticket.number,
                "status": ticket.status,
                "is_priority": ticket.is_priority,
                "people_ahead": ticket.people_ahead,
                "estimated_wait_minutes": ticket.estimated_wait_minutes,
            },
            user=user,
        )