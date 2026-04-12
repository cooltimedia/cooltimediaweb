"""
Kiosk views for the QFlow MVP application.

These views handle the customer-facing kiosk flow:
- display the kiosk home screen
- create new queue tickets
- show the created ticket details
"""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from mvp_qflow_core.forms import KioskTicketForm
from mvp_qflow_core.models import BranchSetting, QueueTicket
from mvp_qflow_core.services.queue_metrics_service import QueueMetricsService
from mvp_qflow_core.services.ticket_creation_service import (
    TicketCreationData,
    TicketCreationService,
)
from mvp_qflow_core.services.ticket_tracking_service import TicketTrackingService
from mvp_qflow_core.services.qr_code_service import QRCodeService


class KioskBranchMixin:
    """
    Shared helper mixin for kiosk views.

    Responsibilities:
    - resolve the active branch from URL kwargs
    - ensure the branch is active
    - make the branch available to child views
    """

    branch_kwarg = "branch_slug"
    branch_context_name = "branch"

    def get_branch(self) -> BranchSetting:
        """
        Returns the active branch resolved from the URL.

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

    def get_branch_summary(self):
        """
        Returns the public queue summary for the active branch.

        Returns:
            BranchQueueSummary: Branch queue summary object.
        """
        branch = self.get_branch()
        return QueueMetricsService.get_branch_public_queue_summary(branch=branch)

    def get_context_data(self, **kwargs):
        """
        Injects branch and branch summary into the view context.
        """
        context = super().get_context_data(**kwargs)
        branch = self.get_branch()

        context[self.branch_context_name] = branch
        context["branch_summary"] = self.get_branch_summary()
        return context


class KioskHomeView(KioskBranchMixin, FormView):
    """
    Displays the kiosk home screen and handles ticket creation.

    This view is the main customer entry point for the kiosk flow.
    """
    template_name = "mvp_qflow_core/kiosk/home.html"
    form_class = KioskTicketForm

    def get_form_kwargs(self):
        """
        Injects the active branch into the form initialization.
        """
        kwargs = super().get_form_kwargs()
        kwargs["branch"] = self.get_branch()
        return kwargs

    def form_valid(self, form):
        """
        Creates a new ticket using the kiosk form payload and redirects
        to the ticket-created page.

        Args:
            form (KioskTicketForm): Valid kiosk form.

        Returns:
            HttpResponseRedirect: Redirect to the created ticket screen.
        """
        created_by = self.request.user if self.request.user.is_authenticated else None

        try:
            payload = form.get_creation_payload(created_by=created_by)
            ticket_data = TicketCreationData(**payload)
            ticket = TicketCreationService.create_ticket(data=ticket_data)

            messages.success(
                self.request,
                f"Ticket {ticket.ticket_code} created successfully.",
            )

            return redirect(
                self.get_success_url(ticket=ticket)
            )

        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

    def get_success_url(self, ticket: QueueTicket) -> str:
        """
        Returns the URL of the ticket-created page for the given ticket.

        Args:
            ticket (QueueTicket): Newly created ticket.

        Returns:
            str: Success URL.
        """
        return reverse(
            "mvp_qflow_core:kiosk_ticket_created",
            kwargs={
                "branch_slug": ticket.branch.slug,
                "internal_token": ticket.internal_token,
            },
        )


class KioskTicketCreatedView(KioskBranchMixin, TemplateView):
    """
    Displays the ticket created confirmation page.

    This page is intended to:
    - show the generated ticket details
    - expose the QR tracking link
    - provide printing context for the thermal ticket view
    """
    template_name = "mvp_qflow_core/kiosk/ticket_created.html"

    token_kwarg = "internal_token"

    def get_ticket(self) -> QueueTicket:
        """
        Resolves the ticket from the internal token and validates that
        it belongs to the branch in the current URL.

        Returns:
            QueueTicket: Matching ticket instance.

        Raises:
            Http404: If the ticket does not belong to the branch.
        """
        internal_token = self.kwargs.get(self.token_kwarg)
        branch = self.get_branch()

        if not internal_token:
            raise Http404("Ticket token is required.")

        try:
            ticket = TicketTrackingService.get_ticket_by_token(
                internal_token=internal_token
            )
        except QueueTicket.DoesNotExist as exc:
            raise Http404("Ticket not found.") from exc
        except ValueError as exc:
            raise Http404(str(exc)) from exc

        if ticket.branch_id != branch.id:
            raise Http404("Ticket does not belong to this branch.")

        return ticket


    def get_context_data(self, **kwargs):
        """
        Adds ticket and tracking context to the page.
        """
        context = super().get_context_data(**kwargs)
        ticket = self.get_ticket()

        tracking_data = TicketTrackingService.get_tracking_data(
            internal_token=ticket.internal_token,
            refresh_snapshot=True,
        )

        tracking_relative_url = reverse(
            "mvp_qflow_core:ticket_tracking",
            kwargs={"internal_token": ticket.internal_token},
        )
        tracking_absolute_url = self.request.build_absolute_uri(tracking_relative_url)

        context["ticket"] = ticket
        context["tracking_data"] = tracking_data
        context["tracking_url"] = tracking_relative_url
        context["tracking_absolute_url"] = tracking_absolute_url
        context["qr_code_data_uri"] = QRCodeService.build_data_uri(
            value=tracking_absolute_url
        )
        context["print_ticket_url"] = reverse(
            "mvp_qflow_core:kiosk_print_ticket",
            kwargs={
                "branch_slug": ticket.branch.slug,
                "internal_token": ticket.internal_token,
            },
        )
        context["should_auto_print"] = (
            ticket.branch.auto_print and not ticket.branch.is_digital_only
        )

        return context

class KioskPrintTicketView(KioskBranchMixin, TemplateView):
    """
    Displays the printable thermal ticket page.

    This page is intended to be rendered in a print-friendly template
    and can be opened in a popup or iframe for browser-based printing.
    """
    template_name = "mvp_qflow_core/print/thermal_ticket.html"

    token_kwarg = "internal_token"

    def get_ticket(self) -> QueueTicket:
        """
        Resolves and validates the ticket for the current branch.

        Returns:
            QueueTicket: Matching ticket instance.

        Raises:
            Http404: If the ticket is invalid for the current branch.
        """
        internal_token = self.kwargs.get(self.token_kwarg)
        branch = self.get_branch()

        if not internal_token:
            raise Http404("Ticket token is required.")

        try:
            ticket = TicketTrackingService.get_ticket_by_token(
                internal_token=internal_token
            )
        except QueueTicket.DoesNotExist as exc:
            raise Http404("Ticket not found.") from exc
        except ValueError as exc:
            raise Http404(str(exc)) from exc

        if ticket.branch_id != branch.id:
            raise Http404("Ticket does not belong to this branch.")

        return ticket


    def get_context_data(self, **kwargs):
        """
        Adds ticket context required for print rendering.
        """
        context = super().get_context_data(**kwargs)
        ticket = self.get_ticket()

        tracking_data = TicketTrackingService.get_tracking_data(
            internal_token=ticket.internal_token,
            refresh_snapshot=True,
        )

        tracking_relative_url = reverse(
            "mvp_qflow_core:ticket_tracking",
            kwargs={"internal_token": ticket.internal_token},
        )
        tracking_absolute_url = self.request.build_absolute_uri(tracking_relative_url)

        context["ticket"] = ticket
        context["tracking_data"] = tracking_data
        context["tracking_url"] = tracking_relative_url
        context["tracking_absolute_url"] = tracking_absolute_url
        context["qr_code_data_uri"] = QRCodeService.build_data_uri(
            value=tracking_absolute_url
        )
        context["show_print_actions"] = True
        return context