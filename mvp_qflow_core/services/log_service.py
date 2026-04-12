"""
Application log service.

This service centralizes application log creation to keep business services
clean, consistent, and easier to maintain.
"""

from typing import Any, Optional

from django.contrib.auth import get_user_model

from mvp_qflow_core.models import (
    AppProcessingLog,
    BranchSetting,
    LogLevel,
    QueueTicket,
    ServiceType,
)

User = get_user_model()


class LogService:
    """
    Centralized helper for writing application logs.

    Responsibilities:
    - Normalize log creation
    - Keep action names consistent
    - Allow any service to write logs with minimal repeated code
    """

    @classmethod
    def create_log(
        cls,
        *,
        level: str = LogLevel.INFO,
        action: str,
        branch: Optional[BranchSetting] = None,
        service_type: Optional[ServiceType] = None,
        ticket: Optional[QueueTicket] = None,
        payload: Optional[dict[str, Any]] = None,
        user: Optional[User] = None,
    ) -> AppProcessingLog:
        """
        Creates a generic application log record.

        Args:
            level (str): Log severity level.
            action (str): Human-readable event description.
            branch (BranchSetting | None): Optional related branch.
            service_type (ServiceType | None): Optional related service.
            ticket (QueueTicket | None): Optional related ticket.
            payload (dict | None): Optional structured metadata.
            user (User | None): Optional related user.

        Returns:
            AppProcessingLog: Created log instance.
        """
        return AppProcessingLog.objects.create(
            branch=branch,
            service_type=service_type,
            ticket=ticket,
            level=level,
            action=action,
            payload=payload or {},
            user=user,
        )

    @classmethod
    def info(
        cls,
        *,
        action: str,
        branch: Optional[BranchSetting] = None,
        service_type: Optional[ServiceType] = None,
        ticket: Optional[QueueTicket] = None,
        payload: Optional[dict[str, Any]] = None,
        user: Optional[User] = None,
    ) -> AppProcessingLog:
        """
        Shortcut for informational logs.
        """
        return cls.create_log(
            level=LogLevel.INFO,
            action=action,
            branch=branch,
            service_type=service_type,
            ticket=ticket,
            payload=payload,
            user=user,
        )

    @classmethod
    def warning(
        cls,
        *,
        action: str,
        branch: Optional[BranchSetting] = None,
        service_type: Optional[ServiceType] = None,
        ticket: Optional[QueueTicket] = None,
        payload: Optional[dict[str, Any]] = None,
        user: Optional[User] = None,
    ) -> AppProcessingLog:
        """
        Shortcut for warning logs.
        """
        return cls.create_log(
            level=LogLevel.WARNING,
            action=action,
            branch=branch,
            service_type=service_type,
            ticket=ticket,
            payload=payload,
            user=user,
        )

    @classmethod
    def error(
        cls,
        *,
        action: str,
        branch: Optional[BranchSetting] = None,
        service_type: Optional[ServiceType] = None,
        ticket: Optional[QueueTicket] = None,
        payload: Optional[dict[str, Any]] = None,
        user: Optional[User] = None,
    ) -> AppProcessingLog:
        """
        Shortcut for error logs.
        """
        return cls.create_log(
            level=LogLevel.ERROR,
            action=action,
            branch=branch,
            service_type=service_type,
            ticket=ticket,
            payload=payload,
            user=user,
        )

    @classmethod
    def critical(
        cls,
        *,
        action: str,
        branch: Optional[BranchSetting] = None,
        service_type: Optional[ServiceType] = None,
        ticket: Optional[QueueTicket] = None,
        payload: Optional[dict[str, Any]] = None,
        user: Optional[User] = None,
    ) -> AppProcessingLog:
        """
        Shortcut for critical logs.
        """
        return cls.create_log(
            level=LogLevel.CRITICAL,
            action=action,
            branch=branch,
            service_type=service_type,
            ticket=ticket,
            payload=payload,
            user=user,
        )