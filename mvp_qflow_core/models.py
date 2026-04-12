"""
Queue Management System - MVP
Description: Core models for managing service queues, branch configurations,
service behavior, ticket lifecycle, public tracking, and operational logs.
Author: Cooltimedia
Date: April 02, 2026
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------
# Choices
# ---------------------------------------------------------

class TicketStatus(models.TextChoices):
    WAITING = "waiting", _("Waiting in Queue")
    CALLED = "called", _("Called to Counter")
    ATTENDING = "attending", _("Currently Being Served")
    FINISHED = "finished", _("Service Completed")
    MISSED = "missed", _("Customer Not Present")
    CANCELLED = "cancelled", _("Cancelled by User/Staff")


class LogLevel(models.TextChoices):
    INFO = "info", _("Information")
    WARNING = "warning", _("Warning")
    ERROR = "error", _("Error")
    CRITICAL = "critical", _("Critical Failure")


class ResetPolicy(models.TextChoices):
    NEVER = "never", _("Never Reset")
    DAILY = "daily", _("Reset Daily")


class CallEventResult(models.TextChoices):
    CALLED = "called", _("Ticket Called")
    NO_RESPONSE = "no_response", _("No Response")
    ANSWERED = "answered", _("Customer Responded")
    AUTO_MISSED = "auto_missed", _("Marked as Missed Automatically")
    MANUAL_MISSED = "manual_missed", _("Marked as Missed Manually")


# ---------------------------------------------------------
# Abstract base model
# ---------------------------------------------------------

class TimeStampedModel(models.Model):
    """
    Adds created and updated timestamps to inheriting models.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------
# Branch configuration
# ---------------------------------------------------------

class BranchSetting(TimeStampedModel):
    """
    Stores branch-level configuration for queue operation, public display,
    digital tracking, and printing behavior.
    """
    name = models.CharField(max_length=100, verbose_name=_("Branch Name"))
    slug = models.SlugField(
        unique=True,
        help_text=_("Unique identifier for URL namespacing.")
    )

    is_active = models.BooleanField(default=True)

    # Queue flow
    is_digital_only = models.BooleanField(
        default=False,
        help_text=_("If True, disables physical thermal printing.")
    )
    auto_print = models.BooleanField(
        default=True,
        help_text=_("If True, attempts browser-based printing after ticket creation.")
    )
    requires_identification = models.BooleanField(
        default=False,
        help_text=_("If True, requests ID/DNI during ticket registration.")
    )

    # Priority flow
    has_priority_lane = models.BooleanField(
        default=True,
        help_text=_("If True, the branch supports priority handling.")
    )

    # Ticket numbering
    reset_policy = models.CharField(
        max_length=20,
        choices=ResetPolicy.choices,
        default=ResetPolicy.DAILY,
        help_text=_("Controls whether ticket numbering resets daily.")
    )

    # Call configuration
    max_call_attempts = models.PositiveSmallIntegerField(
        default=3,
        help_text=_("Maximum number of call attempts before marking the ticket as missed.")
    )
    call_interval_seconds = models.PositiveIntegerField(
        default=20,
        help_text=_("Seconds to wait between call attempts.")
    )

    # Monitoring
    critical_wait_threshold_minutes = models.PositiveIntegerField(
        default=30,
        help_text=_("Minutes before triggering a critical wait alert.")
    )

    # Customer tracking / public display
    enable_qr_tracking = models.BooleanField(default=True)
    allow_customer_cancel = models.BooleanField(default=True)
    show_estimated_wait_time = models.BooleanField(default=True)

    public_message = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Main message shown in kiosk, public display, or ticket tracking pages.")
    )
    secondary_message = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Secondary helper message for customers.")
    )

    class Meta:
        verbose_name = _("Branch Setting")
        verbose_name_plural = _("Branch Settings")
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# Service configuration
# ---------------------------------------------------------

class ServiceType(TimeStampedModel):
    """
    Represents a service queue within a branch.
    Example: Cashier, Customer Service, Laboratory.
    """
    branch = models.ForeignKey(
        BranchSetting,
        on_delete=models.CASCADE,
        related_name="services"
    )
    name = models.CharField(max_length=50, verbose_name=_("Service Name"))
    slug = models.SlugField()
    prefix = models.CharField(
        max_length=5,
        help_text=_("Example: A, B, PR, LAB")
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Service-specific numbering behavior
    use_branch_reset_policy = models.BooleanField(
        default=True,
        help_text=_("If True, uses the branch reset policy.")
    )
    reset_policy = models.CharField(
        max_length=20,
        choices=ResetPolicy.choices,
        default=ResetPolicy.DAILY,
        help_text=_("Only applies when use_branch_reset_policy is False.")
    )

    average_service_time_minutes = models.PositiveIntegerField(
        default=8,
        help_text=_("Average service time used to estimate queue wait time.")
    )

    class Meta:
        verbose_name = _("Service Type")
        verbose_name_plural = _("Service Types")
        ordering = ["branch__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "slug"],
                name="unique_service_slug_per_branch"
            ),
            models.UniqueConstraint(
                fields=["branch", "prefix"],
                name="unique_service_prefix_per_branch"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.prefix}) - {self.branch.name}"

    @property
    def effective_reset_policy(self):
        """
        Returns the effective reset policy for the service.
        """
        if self.use_branch_reset_policy:
            return self.branch.reset_policy
        return self.reset_policy


# ---------------------------------------------------------
# Ticket sequence tracker
# ---------------------------------------------------------

class TicketSequence(TimeStampedModel):
    """
    Stores the last issued number for a branch/service/date scope.
    This supports reset-by-day logic and helps prevent collisions.
    """
    branch = models.ForeignKey(
        BranchSetting,
        on_delete=models.CASCADE,
        related_name="ticket_sequences"
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.CASCADE,
        related_name="ticket_sequences"
    )
    sequence_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Required when numbering resets daily.")
    )
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("Ticket Sequence")
        verbose_name_plural = _("Ticket Sequences")
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "service_type", "sequence_date"],
                name="unique_ticket_sequence_scope"
            )
        ]

    def __str__(self):
        return f"{self.branch.slug} - {self.service_type.prefix} - {self.sequence_date} - {self.last_number}"


# ---------------------------------------------------------
# Main ticket entity
# ---------------------------------------------------------

class QueueTicket(TimeStampedModel):
    """
    Represents a customer's ticket within a queue.
    Includes operational state, priority handling, tracking, and timing.
    """
    branch = models.ForeignKey(
        BranchSetting,
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    # Visible and internal identifiers
    number = models.PositiveIntegerField()
    ticket_code = models.CharField(
        max_length=30,
        help_text=_("Human-readable ticket code like A-101.")
    )
    internal_token = models.CharField(
        max_length=80,
        unique=True,
        help_text=_("Unique collision-resistant token for QR and internal tracking.")
    )

    # Customer data
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_id = models.CharField(max_length=30, blank=True, null=True)
    is_priority = models.BooleanField(default=False)

    # Queue snapshot metrics
    estimated_wait_minutes = models.PositiveIntegerField(default=0)
    people_ahead = models.PositiveIntegerField(default=0)

    # Ticket lifecycle
    status = models.CharField(
        max_length=20,
        choices=TicketStatus.choices,
        default=TicketStatus.WAITING
    )
    called_at = models.DateTimeField(null=True, blank=True)
    service_start_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    missed_at = models.DateTimeField(null=True, blank=True)

    # Call tracking
    call_attempts = models.PositiveSmallIntegerField(default=0)

    # Staff attribution
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qflow_attended_tickets"
    )

    class Meta:
        verbose_name = _("Queue Ticket")
        verbose_name_plural = _("Queue Tickets")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["branch", "service_type", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["ticket_code"]),
            models.Index(fields=["internal_token"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.ticket_code} - {self.status}"

    @property
    def is_open(self):
        """
        Returns True if the ticket is still active in the queue lifecycle.
        """
        return self.status in {
            TicketStatus.WAITING,
            TicketStatus.CALLED,
            TicketStatus.ATTENDING,
        }


# ---------------------------------------------------------
# Ticket call history
# ---------------------------------------------------------

class TicketCall(TimeStampedModel):
    """
    Stores each call attempt or call-related event for a ticket.
    Useful for retries, auditing, and automatic missed handling.
    """
    ticket = models.ForeignKey(
        QueueTicket,
        on_delete=models.CASCADE,
        related_name="call_events"
    )
    attempt_number = models.PositiveSmallIntegerField(default=1)
    result = models.CharField(
        max_length=20,
        choices=CallEventResult.choices,
        default=CallEventResult.CALLED
    )
    called_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qflow_ticket_calls"
    )
    notes = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _("Ticket Call Event")
        verbose_name_plural = _("Ticket Call Events")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["ticket", "attempt_number"]),
            models.Index(fields=["result", "created_at"]),
        ]

    def __str__(self):
        return f"{self.ticket.ticket_code} - Attempt {self.attempt_number}"


# ---------------------------------------------------------
# Application logs
# ---------------------------------------------------------

class AppProcessingLog(TimeStampedModel):
    """
    Audit trail for system events, printing failures, queue alerts,
    state changes, and user operations.
    """
    branch = models.ForeignKey(
        BranchSetting,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="processing_logs"
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="processing_logs"
    )
    ticket = models.ForeignKey(
        QueueTicket,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="processing_logs"
    )
    level = models.CharField(
        max_length=10,
        choices=LogLevel.choices,
        default=LogLevel.INFO
    )
    action = models.CharField(
        max_length=255,
        help_text=_("Description of the event, for example 'Ticket created' or 'Printing failure'.")
    )
    payload = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Optional metadata or raw error details.")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qflow_processing_logs"
    )

    class Meta:
        verbose_name = _("Processing Log")
        verbose_name_plural = _("Processing Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["level", "created_at"]),
            models.Index(fields=["branch", "created_at"]),
            models.Index(fields=["ticket", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.level.upper()}] {self.action}"