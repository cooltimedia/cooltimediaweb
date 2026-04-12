"""
Ticket sequence service.

This service is responsible for resolving the next valid ticket number
for a given branch and service, based on the configured reset policy.
"""

from django.db import transaction
from django.utils import timezone

from mvp_qflow_core.models import (
    ResetPolicy,
    ServiceType,
    TicketSequence,
)


class TicketSequenceService:
    """
    Handles ticket numbering logic for queue tickets.

    Responsibilities:
    - Resolve the effective reset policy for a service
    - Determine the sequence scope date
    - Create or lock the correct TicketSequence row
    - Increment and return the next ticket number safely
    """

    @classmethod
    def get_next_number(cls, service_type: ServiceType) -> int:
        """
        Returns the next ticket number for the given service.

        This method uses a database transaction and row-level locking
        to reduce the risk of collisions when multiple requests try
        to create tickets at the same time.

        Args:
            service_type (ServiceType): The service for which the next
                ticket number should be generated.

        Returns:
            int: The next available numeric ticket value.
        """
        if not service_type:
            raise ValueError("service_type is required.")

        if not service_type.branch_id:
            raise ValueError("service_type must belong to a branch.")

        sequence_date = cls._get_sequence_date(service_type=service_type)

        with transaction.atomic():
            sequence = cls._get_or_create_locked_sequence(
                service_type=service_type,
                sequence_date=sequence_date,
            )

            sequence.last_number += 1
            sequence.save(update_fields=["last_number", "updated_at"])

            return sequence.last_number

    @classmethod
    def _get_or_create_locked_sequence(
        cls,
        service_type: ServiceType,
        sequence_date,
    ) -> TicketSequence:
        """
        Retrieves and locks the sequence row for the given scope.

        If the sequence row does not exist yet, it is created first and
        then fetched again with select_for_update().

        Args:
            service_type (ServiceType): The target service.
            sequence_date (date | None): Date scope for the sequence.
                If None, the sequence is considered non-daily.

        Returns:
            TicketSequence: A locked sequence row ready to be incremented.
        """
        branch = service_type.branch

        sequence = (
            TicketSequence.objects.select_for_update()
            .filter(
                branch=branch,
                service_type=service_type,
                sequence_date=sequence_date,
            )
            .first()
        )

        if sequence:
            return sequence

        TicketSequence.objects.create(
            branch=branch,
            service_type=service_type,
            sequence_date=sequence_date,
            last_number=0,
        )

        return (
            TicketSequence.objects.select_for_update()
            .get(
                branch=branch,
                service_type=service_type,
                sequence_date=sequence_date,
            )
        )

    @classmethod
    def _get_sequence_date(cls, service_type: ServiceType):
        """
        Returns the date scope used for the ticket sequence.

        If the effective reset policy is DAILY, the current local date is used.
        If the policy is NEVER, the sequence date is None, meaning that the
        numbering continues indefinitely.

        Args:
            service_type (ServiceType): The service whose reset policy is used.

        Returns:
            date | None: The date scope for the sequence.
        """
        effective_policy = cls._get_effective_reset_policy(service_type=service_type)

        if effective_policy == ResetPolicy.DAILY:
            return timezone.localdate()

        return None

    @staticmethod
    def _get_effective_reset_policy(service_type: ServiceType) -> str:
        """
        Resolves the effective reset policy for the service.

        Args:
            service_type (ServiceType): The service instance.

        Returns:
            str: A value from ResetPolicy.
        """
        return service_type.effective_reset_policy