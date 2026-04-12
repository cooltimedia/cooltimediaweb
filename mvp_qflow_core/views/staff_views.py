"""
Staff views for the QFlow MVP application.

These views handle operational queue management for branch staff:
- dashboard overview
- calling tickets
- marking no response
- starting service
- finishing service
- cancelling tickets
- marking tickets as missed manually

Access to this module is restricted to authenticated users who belong
to allowed QFlow staff groups or are superusers.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from mvp_qflow_core.models import BranchSetting, QueueTicket, ServiceType, TicketStatus
from mvp_qflow_core.services.queue_metrics_service import QueueMetricsService
from mvp_qflow_core.services.ticket_call_service import TicketCallService


QFLOW_STAFF_ALLOWED_GROUPS = {
    "qflow_staff",
    "qflow_supervisor",
    "qflow_admin",
}


class QFlowStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Restricts access to authenticated users who belong to
    allowed QFlow staff groups.

    Rules:
    - Superusers are always allowed
    - Authenticated users must belong to at least one allowed group
    """

    login_url = "wagtailadmin_login"
    raise_exception = False
    allowed_groups = QFLOW_STAFF_ALLOWED_GROUPS

    def test_func(self):
        """
        Returns True when the user is authorized to access QFlow staff views.
        """
        user = self.request.user

        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.groups.filter(name__in=self.allowed_groups).exists()

    def handle_no_permission(self):
        """
        Redirects anonymous users to login and raises PermissionDenied
        for authenticated users without the required group membership.
        """
        if self.request.user.is_authenticated:
            raise PermissionDenied("You do not have access to this staff area.")
        return super().handle_no_permission()


class StaffBranchMixin:
    """
    Shared helper mixin for staff views.

    Responsibilities:
    - resolve the active branch from URL kwargs
    - centralize branch validation
    - provide common dashboard redirects
    """

    branch_kwarg = "branch_slug"
    service_kwarg = "service_id"
    ticket_kwarg = "ticket_id"

    def get_branch(self) -> BranchSetting:
        """
        Resolves the active branch from the URL.

        Returns:
            BranchSetting: Active branch instance.

        Raises:
            Http404: If the branch does not exist or is inactive.
        """
        branch_slug = self.kwargs.get(self.branch_kwarg)

        if not branch_slug:
            raise Http404("Branch slug is required.")

        return get_object_or_404(
            BranchSetting,
            slug=branch_slug,
            is_active=True,
        )

    def get_service(self) -> ServiceType:
        """
        Resolves a service that belongs to the current branch.

        Returns:
            ServiceType: Matching service instance.

        Raises:
            Http404: If the service does not belong to the current branch.
        """
        branch = self.get_branch()
        service_id = self.kwargs.get(self.service_kwarg)

        if not service_id:
            raise Http404("Service id is required.")

        return get_object_or_404(
            ServiceType.objects.select_related("branch"),
            pk=service_id,
            branch=branch,
            is_active=True,
        )

    def get_ticket(self) -> QueueTicket:
        """
        Resolves a ticket that belongs to the current branch.

        Returns:
            QueueTicket: Matching ticket instance.

        Raises:
            Http404: If the ticket does not belong to the current branch.
        """
        branch = self.get_branch()
        ticket_id = self.kwargs.get(self.ticket_kwarg)

        if not ticket_id:
            raise Http404("Ticket id is required.")

        return get_object_or_404(
            QueueTicket.objects.select_related("branch", "service_type", "assigned_agent"),
            pk=ticket_id,
            branch=branch,
        )

    def get_dashboard_url(self) -> str:
        """
        Returns the dashboard URL for the current branch.
        """
        return reverse(
            "mvp_qflow_core:staff_dashboard",
            kwargs={"branch_slug": self.get_branch().slug},
        )


class StaffDashboardView(QFlowStaffRequiredMixin, StaffBranchMixin, TemplateView):
    """
    Displays the main operational dashboard for a branch.

    The dashboard is intended to show:
    - branch queue summary
    - service queue summaries
    - current called/attending tickets
    - next waiting tickets
    - direct operational actions
    """
    template_name = "mvp_qflow_core/staff/dashboard.html"

    def get_context_data(self, **kwargs):
        """
        Adds branch and rich queue summary context to the dashboard.
        """
        context = super().get_context_data(**kwargs)
        branch = self.get_branch()
        staff_branch_summary = QueueMetricsService.get_staff_branch_queue_summary(
            branch=branch
        )

        context["branch"] = branch
        context["branch_summary"] = staff_branch_summary
        context["page_title"] = f"{branch.name} Staff Dashboard"
        context["total_open_tickets"] = staff_branch_summary.total_open_tickets
        context["total_waiting_tickets"] = staff_branch_summary.total_waiting_tickets
        context["total_called_tickets"] = staff_branch_summary.total_called_tickets
        context["total_attending_tickets"] = staff_branch_summary.total_attending_tickets
        return context


class StaffCallNextTicketView(QFlowStaffRequiredMixin, StaffBranchMixin, View):
    """
    Calls the next waiting ticket for a given service.

    Queue ordering rule for MVP:
    - priority waiting tickets first
    - then standard waiting tickets
    - oldest first within each group
    """

    def post(self, request, *args, **kwargs):
        """
        Calls the next available waiting ticket for the selected service.
        """
        service = self.get_service()

        next_ticket = (
            QueueTicket.objects.select_related("branch", "service_type", "assigned_agent")
            .filter(
                branch=service.branch,
                service_type=service,
                status=TicketStatus.WAITING,
            )
            .order_by("-is_priority", "created_at")
            .first()
        )

        if not next_ticket:
            messages.warning(
                request,
                f"No waiting tickets found for {service.name}.",
            )
            return redirect(self.get_dashboard_url())

        try:
            result = TicketCallService.call_ticket(
                ticket=next_ticket,
                called_by=request.user if request.user.is_authenticated else None,
                notes=f"Called from staff dashboard for service {service.name}.",
            )
            messages.success(request, result.message)
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(self.get_dashboard_url())


class StaffRecallTicketView(QFlowStaffRequiredMixin, StaffBranchMixin, View):
    """
    Calls a specific ticket again or calls it directly if it is still waiting.
    """

    def post(self, request, *args, **kwargs):
        """
        Calls the selected ticket.
        """
        ticket = self.get_ticket()

        try:
            result = TicketCallService.call_ticket(
                ticket=ticket,
                called_by=request.user if request.user.is_authenticated else None,
                notes="Ticket called manually from staff dashboard.",
            )
            messages.success(request, result.message)
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(self.get_dashboard_url())


class StaffNoResponseView(QFlowStaffRequiredMixin, StaffBranchMixin, View):
    """
    Registers that the customer did not respond to the current call.
    """

    def post(self, request, *args, **kwargs):
        """
        Records a no-response event for the selected ticket.
        """
        ticket = self.get_ticket()

        try:
            result = TicketCallService.mark_no_response(
                ticket=ticket,
                user=request.user if request.user.is_authenticated else None,
                notes="No response registered from staff dashboard.",
            )
            messages.warning(request, result.message)
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(self.get_dashboard_url())


class StaffStartServiceView(QFlowStaffRequiredMixin, StaffBranchMixin, View):
    """
    Starts service for a called ticket.
    """

    def post(self, request, *args, **kwargs):
        """
        Moves the selected ticket into ATTENDING status.
        """
        ticket = self.get_ticket()

        try:
            result = TicketCallService.start_service(
                ticket=ticket,
                user=request.user if request.user.is_authenticated else None,
                notes="Service started from staff dashboard.",
            )
            messages.success(request, result.message)
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(self.get_dashboard_url())


class StaffFinishServiceView(QFlowStaffRequiredMixin, StaffBranchMixin, View):
    """
    Finishes service for an attending ticket.
    """

    def post(self, request, *args, **kwargs):
        """
        Moves the selected ticket into FINISHED status.
        """
        ticket = self.get_ticket()

        try:
            result = TicketCallService.finish_service(
                ticket=ticket,
                user=request.user if request.user.is_authenticated else None,
                notes="Service finished from staff dashboard.",
            )
            messages.success(request, result.message)
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(self.get_dashboard_url())


class StaffCancelTicketView(QFlowStaffRequiredMixin, StaffBranchMixin, View):
    """
    Cancels an active ticket from the staff dashboard.
    """

    def post(self, request, *args, **kwargs):
        """
        Cancels the selected ticket.
        """
        ticket = self.get_ticket()

        try:
            result = TicketCallService.cancel_ticket(
                ticket=ticket,
                user=request.user if request.user.is_authenticated else None,
                notes="Ticket cancelled by staff from dashboard.",
                cancelled_by_customer=False,
            )
            messages.warning(request, result.message)
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(self.get_dashboard_url())


class StaffMarkMissedTicketView(QFlowStaffRequiredMixin, StaffBranchMixin, View):
    """
    Marks a ticket as missed manually from the staff dashboard.
    """

    def post(self, request, *args, **kwargs):
        """
        Marks the selected ticket as MISSED.
        """
        ticket = self.get_ticket()

        try:
            result = TicketCallService.mark_missed_manually(
                ticket=ticket,
                user=request.user if request.user.is_authenticated else None,
                notes="Ticket marked as missed manually from staff dashboard.",
            )
            messages.warning(request, result.message)
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(self.get_dashboard_url())