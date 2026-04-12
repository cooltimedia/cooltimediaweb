"""
Queue metrics service.

This service centralizes queue-related read operations and metrics
used across the kiosk, ticket tracking page, staff dashboard,
and public queue display.
"""

from dataclasses import dataclass, asdict
from typing import Optional

from django.db.models import Count, Q, QuerySet

from mvp_qflow_core.models import (
    BranchSetting,
    QueueTicket,
    ServiceType,
    TicketStatus,
)


@dataclass
class TicketQueueMetrics:
    """
    Structured metrics for a single ticket inside a queue context.
    """
    ticket_id: int
    ticket_code: str
    status: str
    people_ahead: int
    estimated_wait_minutes: int
    service_name: str
    service_prefix: str
    branch_name: str
    is_priority: bool


@dataclass
class ServiceQueueSummary:
    """
    Structured summary for a single service queue.
    """
    service_id: int
    service_name: str
    service_slug: str
    service_prefix: str
    average_service_time_minutes: int
    total_open_tickets: int
    waiting_tickets: int
    called_tickets: int
    attending_tickets: int
    finished_tickets: int
    missed_tickets: int
    cancelled_tickets: int
    priority_open_tickets: int
    current_called_ticket: Optional[str]
    current_attending_ticket: Optional[str]
    next_waiting_tickets: list[str]
    estimated_wait_for_new_ticket_minutes: int


@dataclass
class BranchQueueSummary:
    """
    Structured summary for all queues within a branch.
    """
    branch_id: int
    branch_name: str
    branch_slug: str
    public_message: Optional[str]
    secondary_message: Optional[str]
    services: list[ServiceQueueSummary]

@dataclass
class StaffTicketItem:
    """
    Lightweight staff-facing ticket representation used in the staff dashboard.
    """
    id: int
    ticket_code: str
    status: str
    status_label: str
    is_priority: bool
    customer_name: Optional[str]
    customer_id: Optional[str]
    people_ahead: int
    estimated_wait_minutes: int
    call_attempts: int
    created_at: str


@dataclass
class StaffServiceQueueSummary:
    """
    Rich service summary for staff operations.

    Includes counts plus concrete ticket objects that can be used
    to render operational buttons in the dashboard.
    """
    service_id: int
    service_name: str
    service_slug: str
    service_prefix: str
    average_service_time_minutes: int
    total_open_tickets: int
    waiting_tickets: int
    called_tickets: int
    attending_tickets: int
    finished_tickets: int
    missed_tickets: int
    cancelled_tickets: int
    priority_open_tickets: int
    estimated_wait_for_new_ticket_minutes: int
    current_called_ticket: Optional[StaffTicketItem]
    current_attending_ticket: Optional[StaffTicketItem]
    next_waiting_tickets: list[StaffTicketItem]


@dataclass
class StaffBranchQueueSummary:
    """
    Rich branch summary used by the staff dashboard.
    """
    branch_id: int
    branch_name: str
    branch_slug: str
    public_message: Optional[str]
    secondary_message: Optional[str]
    total_open_tickets: int
    total_waiting_tickets: int
    total_called_tickets: int
    total_attending_tickets: int
    services: list[StaffServiceQueueSummary]


class QueueMetricsService:
    """
    Read-only service for queue metrics and queue summaries.

    Responsibilities:
    - Centralize queue-related calculations
    - Keep queue visibility logic consistent across the application
    - Support kiosk, tracking, staff, and public display features
    """

    OPEN_STATUSES = [
        TicketStatus.WAITING,
        TicketStatus.CALLED,
        TicketStatus.ATTENDING,
    ]

    @classmethod
    def get_open_tickets_queryset(
        cls,
        *,
        branch: Optional[BranchSetting] = None,
        service_type: Optional[ServiceType] = None,
        is_priority: Optional[bool] = None,
    ) -> QuerySet:
        """
        Returns a queryset of open tickets filtered by optional scope.

        Open tickets are considered:
        - waiting
        - called
        - attending

        Args:
            branch (BranchSetting | None): Optional branch filter.
            service_type (ServiceType | None): Optional service filter.
            is_priority (bool | None): Optional priority filter.

        Returns:
            QuerySet: Filtered queryset of open tickets.
        """
        queryset = QueueTicket.objects.filter(status__in=cls.OPEN_STATUSES)

        if branch is not None:
            queryset = queryset.filter(branch=branch)

        if service_type is not None:
            queryset = queryset.filter(service_type=service_type)

        if is_priority is not None:
            queryset = queryset.filter(is_priority=is_priority)

        return queryset.select_related("branch", "service_type", "assigned_agent")

    @classmethod
    def count_people_ahead(cls, ticket: QueueTicket) -> int:
        """
        Calculates how many open tickets are ahead of the given ticket.

        MVP rule:
        - If the branch has a priority lane and the ticket is priority,
          only open priority tickets created earlier in the same service
          are counted ahead.
        - Otherwise, all open tickets created earlier in the same service
          are counted ahead.

        Args:
            ticket (QueueTicket): Target ticket.

        Returns:
            int: Number of people ahead in the queue.
        """
        cls._validate_ticket_instance(ticket=ticket)

        queryset = cls.get_open_tickets_queryset(
            branch=ticket.branch,
            service_type=ticket.service_type,
        ).filter(created_at__lt=ticket.created_at)

        if ticket.branch.has_priority_lane and ticket.is_priority:
            queryset = queryset.filter(is_priority=True)

        return queryset.count()

    @classmethod
    def estimate_wait_time_for_ticket(cls, ticket: QueueTicket) -> int:
        """
        Calculates the estimated waiting time for an existing ticket.

        Formula:
            people_ahead * average_service_time_minutes

        Args:
            ticket (QueueTicket): Target ticket.

        Returns:
            int: Estimated waiting time in minutes.
        """
        cls._validate_ticket_instance(ticket=ticket)

        people_ahead = cls.count_people_ahead(ticket=ticket)
        average_service_time = ticket.service_type.average_service_time_minutes or 0

        return people_ahead * average_service_time

    @classmethod
    def get_ticket_queue_metrics(cls, ticket: QueueTicket) -> TicketQueueMetrics:
        """
        Returns a structured queue summary for a single ticket.

        Args:
            ticket (QueueTicket): Target ticket.

        Returns:
            TicketQueueMetrics: Queue metrics for the ticket.
        """
        cls._validate_ticket_instance(ticket=ticket)

        people_ahead = 0
        estimated_wait_minutes = 0

        if ticket.status in cls.OPEN_STATUSES:
            people_ahead = cls.count_people_ahead(ticket=ticket)
            estimated_wait_minutes = cls.estimate_wait_time_for_ticket(ticket=ticket)

        return TicketQueueMetrics(
            ticket_id=ticket.id,
            ticket_code=ticket.ticket_code,
            status=ticket.status,
            people_ahead=people_ahead,
            estimated_wait_minutes=estimated_wait_minutes,
            service_name=ticket.service_type.name,
            service_prefix=ticket.service_type.prefix,
            branch_name=ticket.branch.name,
            is_priority=ticket.is_priority,
        )

    @classmethod
    def get_current_called_ticket(cls, service_type: ServiceType) -> Optional[QueueTicket]:
        """
        Returns the most recent ticket currently in CALLED status for a service.

        Args:
            service_type (ServiceType): Target service.

        Returns:
            QueueTicket | None: Current called ticket, if any.
        """
        return (
            QueueTicket.objects.filter(
                service_type=service_type,
                status=TicketStatus.CALLED,
            )
            .select_related("branch", "service_type", "assigned_agent")
            .order_by("-called_at", "created_at")
            .first()
        )

    @classmethod
    def get_current_attending_ticket(cls, service_type: ServiceType) -> Optional[QueueTicket]:
        """
        Returns the most recent ticket currently in ATTENDING status for a service.

        Args:
            service_type (ServiceType): Target service.

        Returns:
            QueueTicket | None: Current attending ticket, if any.
        """
        return (
            QueueTicket.objects.filter(
                service_type=service_type,
                status=TicketStatus.ATTENDING,
            )
            .select_related("branch", "service_type", "assigned_agent")
            .order_by("-service_start_at", "created_at")
            .first()
        )

    @classmethod
    def get_next_waiting_tickets(
        cls,
        service_type: ServiceType,
        limit: int = 5,
    ) -> QuerySet:
        """
        Returns the next waiting tickets for a service.

        MVP ordering rule:
        - If the branch has priority enabled, priority waiting tickets
          are shown first, then regular waiting tickets.
        - Inside each group, older tickets come first.

        Args:
            service_type (ServiceType): Target service.
            limit (int): Maximum number of tickets to return.

        Returns:
            QuerySet: Ordered queryset of next waiting tickets.
        """
        queryset = QueueTicket.objects.filter(
            service_type=service_type,
            status=TicketStatus.WAITING,
        ).select_related("branch", "service_type")

        if service_type.branch.has_priority_lane:
            queryset = queryset.order_by("-is_priority", "created_at")
        else:
            queryset = queryset.order_by("-is_priority", "created_at")

        return queryset[:limit]

    @classmethod
    def estimate_wait_time_for_new_ticket(cls, service_type: ServiceType) -> int:
        """
        Estimates the waiting time for a newly created standard ticket.

        This uses the number of currently open tickets and the average
        service time configured for the service.

        Args:
            service_type (ServiceType): Target service.

        Returns:
            int: Estimated waiting time in minutes.
        """
        open_count = cls.get_open_tickets_queryset(service_type=service_type).count()
        average_service_time = service_type.average_service_time_minutes or 0
        return open_count * average_service_time

    @classmethod
    def get_service_queue_summary(cls, service_type: ServiceType) -> ServiceQueueSummary:
        """
        Returns a structured queue summary for a specific service.

        Args:
            service_type (ServiceType): Target service.

        Returns:
            ServiceQueueSummary: Summary object for the service queue.
        """
        ticket_counts = cls._get_service_ticket_counts(service_type=service_type)

        current_called = cls.get_current_called_ticket(service_type=service_type)
        current_attending = cls.get_current_attending_ticket(service_type=service_type)
        next_waiting = cls.get_next_waiting_tickets(service_type=service_type, limit=5)

        return ServiceQueueSummary(
            service_id=service_type.id,
            service_name=service_type.name,
            service_slug=service_type.slug,
            service_prefix=service_type.prefix,
            average_service_time_minutes=service_type.average_service_time_minutes,
            total_open_tickets=ticket_counts["total_open_tickets"],
            waiting_tickets=ticket_counts["waiting_tickets"],
            called_tickets=ticket_counts["called_tickets"],
            attending_tickets=ticket_counts["attending_tickets"],
            finished_tickets=ticket_counts["finished_tickets"],
            missed_tickets=ticket_counts["missed_tickets"],
            cancelled_tickets=ticket_counts["cancelled_tickets"],
            priority_open_tickets=ticket_counts["priority_open_tickets"],
            current_called_ticket=current_called.ticket_code if current_called else None,
            current_attending_ticket=current_attending.ticket_code if current_attending else None,
            next_waiting_tickets=[ticket.ticket_code for ticket in next_waiting],
            estimated_wait_for_new_ticket_minutes=cls.estimate_wait_time_for_new_ticket(
                service_type=service_type
            ),
        )

    @classmethod
    def get_branch_public_queue_summary(cls, branch: BranchSetting) -> BranchQueueSummary:
        """
        Returns a full public-facing queue summary for a branch.

        This is useful for:
        - public display screens
        - kiosk summaries
        - dashboard overview pages

        Args:
            branch (BranchSetting): Target branch.

        Returns:
            BranchQueueSummary: Branch-level queue summary.
        """
        services = (
            ServiceType.objects.filter(branch=branch, is_active=True)
            .select_related("branch")
            .order_by("name")
        )

        service_summaries = [
            cls.get_service_queue_summary(service_type=service)
            for service in services
        ]

        return BranchQueueSummary(
            branch_id=branch.id,
            branch_name=branch.name,
            branch_slug=branch.slug,
            public_message=branch.public_message,
            secondary_message=branch.secondary_message,
            services=service_summaries,
        )

    @classmethod
    def refresh_ticket_snapshot(cls, ticket: QueueTicket) -> QueueTicket:
        """
        Recalculates and updates the stored snapshot fields for a ticket.

        This method updates:
        - people_ahead
        - estimated_wait_minutes

        Useful when:
        - rendering the tracking page
        - staff wants refreshed data
        - public queue metrics need consistency

        Args:
            ticket (QueueTicket): Target ticket.

        Returns:
            QueueTicket: Updated ticket instance.
        """
        cls._validate_ticket_instance(ticket=ticket)

        if ticket.status not in cls.OPEN_STATUSES:
            ticket.people_ahead = 0
            ticket.estimated_wait_minutes = 0
        else:
            ticket.people_ahead = cls.count_people_ahead(ticket=ticket)
            ticket.estimated_wait_minutes = cls.estimate_wait_time_for_ticket(ticket=ticket)

        ticket.save(
            update_fields=[
                "people_ahead",
                "estimated_wait_minutes",
                "updated_at",
            ]
        )

        return ticket

    @classmethod
    def serialize_ticket_metrics(cls, ticket: QueueTicket) -> dict:
        """
        Returns ticket queue metrics as a dictionary.

        Useful for JSON responses.

        Args:
            ticket (QueueTicket): Target ticket.

        Returns:
            dict: Serialized ticket metrics.
        """
        metrics = cls.get_ticket_queue_metrics(ticket=ticket)
        return asdict(metrics)

    @classmethod
    def serialize_service_summary(cls, service_type: ServiceType) -> dict:
        """
        Returns a service queue summary as a dictionary.

        Useful for API responses or template contexts.

        Args:
            service_type (ServiceType): Target service.

        Returns:
            dict: Serialized service summary.
        """
        summary = cls.get_service_queue_summary(service_type=service_type)
        return asdict(summary)

    @classmethod
    def serialize_branch_summary(cls, branch: BranchSetting) -> dict:
        """
        Returns a branch queue summary as a dictionary.

        Useful for API responses or template contexts.

        Args:
            branch (BranchSetting): Target branch.

        Returns:
            dict: Serialized branch summary.
        """
        summary = cls.get_branch_public_queue_summary(branch=branch)
        return asdict(summary)

    @classmethod
    def _get_service_ticket_counts(cls, service_type: ServiceType) -> dict:
        """
        Aggregates queue counts for a single service.

        Args:
            service_type (ServiceType): Target service.

        Returns:
            dict: Count summary by queue state.
        """
        base_queryset = QueueTicket.objects.filter(service_type=service_type)

        aggregated = base_queryset.aggregate(
            waiting_tickets=Count("id", filter=Q(status=TicketStatus.WAITING)),
            called_tickets=Count("id", filter=Q(status=TicketStatus.CALLED)),
            attending_tickets=Count("id", filter=Q(status=TicketStatus.ATTENDING)),
            finished_tickets=Count("id", filter=Q(status=TicketStatus.FINISHED)),
            missed_tickets=Count("id", filter=Q(status=TicketStatus.MISSED)),
            cancelled_tickets=Count("id", filter=Q(status=TicketStatus.CANCELLED)),
            priority_open_tickets=Count(
                "id",
                filter=Q(status__in=cls.OPEN_STATUSES, is_priority=True),
            ),
            total_open_tickets=Count(
                "id",
                filter=Q(status__in=cls.OPEN_STATUSES),
            ),
        )

        return {
            "waiting_tickets": aggregated["waiting_tickets"] or 0,
            "called_tickets": aggregated["called_tickets"] or 0,
            "attending_tickets": aggregated["attending_tickets"] or 0,
            "finished_tickets": aggregated["finished_tickets"] or 0,
            "missed_tickets": aggregated["missed_tickets"] or 0,
            "cancelled_tickets": aggregated["cancelled_tickets"] or 0,
            "priority_open_tickets": aggregated["priority_open_tickets"] or 0,
            "total_open_tickets": aggregated["total_open_tickets"] or 0,
        }

    @staticmethod
    def _validate_ticket_instance(ticket: QueueTicket) -> None:
        """
        Validates that the given object is a saved QueueTicket instance.

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
        
    @classmethod
    def get_staff_service_queue_summary(cls, service_type: ServiceType) -> StaffServiceQueueSummary:
        """
        Returns a rich queue summary for a service, including concrete ticket
        objects needed for staff dashboard actions.

        Args:
            service_type (ServiceType): Target service.

        Returns:
            StaffServiceQueueSummary: Staff-ready service summary.
        """
        ticket_counts = cls._get_service_ticket_counts(service_type=service_type)

        current_called = cls.get_current_called_ticket(service_type=service_type)
        current_attending = cls.get_current_attending_ticket(service_type=service_type)
        next_waiting_queryset = cls.get_next_waiting_tickets(service_type=service_type, limit=5)

        next_waiting_tickets = [
            cls._serialize_staff_ticket_item(ticket=ticket)
            for ticket in next_waiting_queryset
        ]

        return StaffServiceQueueSummary(
            service_id=service_type.id,
            service_name=service_type.name,
            service_slug=service_type.slug,
            service_prefix=service_type.prefix,
            average_service_time_minutes=service_type.average_service_time_minutes,
            total_open_tickets=ticket_counts["total_open_tickets"],
            waiting_tickets=ticket_counts["waiting_tickets"],
            called_tickets=ticket_counts["called_tickets"],
            attending_tickets=ticket_counts["attending_tickets"],
            finished_tickets=ticket_counts["finished_tickets"],
            missed_tickets=ticket_counts["missed_tickets"],
            cancelled_tickets=ticket_counts["cancelled_tickets"],
            priority_open_tickets=ticket_counts["priority_open_tickets"],
            estimated_wait_for_new_ticket_minutes=cls.estimate_wait_time_for_new_ticket(
                service_type=service_type
            ),
            current_called_ticket=cls._serialize_staff_ticket_item(current_called)
            if current_called else None,
            current_attending_ticket=cls._serialize_staff_ticket_item(current_attending)
            if current_attending else None,
            next_waiting_tickets=next_waiting_tickets,
        )

    @classmethod
    def get_staff_branch_queue_summary(cls, branch: BranchSetting) -> StaffBranchQueueSummary:
        """
        Returns a rich branch summary for the staff dashboard.

        Args:
            branch (BranchSetting): Target branch.

        Returns:
            StaffBranchQueueSummary: Staff-ready branch summary.
        """
        services = (
            ServiceType.objects.filter(branch=branch, is_active=True)
            .select_related("branch")
            .order_by("name")
        )

        service_summaries = [
            cls.get_staff_service_queue_summary(service_type=service)
            for service in services
        ]

        total_open_tickets = sum(service.total_open_tickets for service in service_summaries)
        total_waiting_tickets = sum(service.waiting_tickets for service in service_summaries)
        total_called_tickets = sum(service.called_tickets for service in service_summaries)
        total_attending_tickets = sum(service.attending_tickets for service in service_summaries)

        return StaffBranchQueueSummary(
            branch_id=branch.id,
            branch_name=branch.name,
            branch_slug=branch.slug,
            public_message=branch.public_message,
            secondary_message=branch.secondary_message,
            total_open_tickets=total_open_tickets,
            total_waiting_tickets=total_waiting_tickets,
            total_called_tickets=total_called_tickets,
            total_attending_tickets=total_attending_tickets,
            services=service_summaries,
        )

    @classmethod
    def _serialize_staff_ticket_item(cls, ticket: Optional[QueueTicket]) -> Optional[StaffTicketItem]:
        """
        Builds a lightweight staff-facing ticket representation.

        Args:
            ticket (QueueTicket | None): Target ticket.

        Returns:
            StaffTicketItem | None: Serialized ticket item.
        """
        if not ticket:
            return None

        people_ahead = 0
        estimated_wait_minutes = 0

        if ticket.status in cls.OPEN_STATUSES:
            people_ahead = cls.count_people_ahead(ticket=ticket)
            estimated_wait_minutes = cls.estimate_wait_time_for_ticket(ticket=ticket)

        return StaffTicketItem(
            id=ticket.id,
            ticket_code=ticket.ticket_code,
            status=ticket.status,
            status_label=ticket.get_status_display(),
            is_priority=ticket.is_priority,
            customer_name=ticket.customer_name,
            customer_id=ticket.customer_id,
            people_ahead=people_ahead,
            estimated_wait_minutes=estimated_wait_minutes,
            call_attempts=ticket.call_attempts,
            created_at=ticket.created_at.isoformat(),
        )