"""
Tracking views for the QFlow MVP application.

These views handle the customer-facing tracking flow:
- display ticket tracking details from the QR/internal token
- process customer ticket cancellation when allowed
"""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from mvp_qflow_core.forms import TicketTrackingCancelForm
from mvp_qflow_core.models import QueueTicket
from mvp_qflow_core.services.ticket_tracking_service import TicketTrackingService
from mvp_qflow_core.services.qr_code_service import QRCodeService


class TicketTrackingMixin:
    """
    Shared helper mixin for ticket tracking views.

    Responsibilities:
    - resolve the ticket from the internal token
    - centralize token validation and 404 handling
    """

    token_kwarg = "internal_token"
    ticket_context_name = "ticket"

    def get_internal_token(self) -> str:
        """
        Returns the tracking token from the URL kwargs.

        Returns:
            str: Internal tracking token.

        Raises:
            Http404: If the token is missing.
        """
        internal_token = self.kwargs.get(self.token_kwarg)

        if not internal_token:
            raise Http404("Ticket token is required.")

        return internal_token

    def get_ticket(self) -> QueueTicket:
        """
        Resolves the ticket from the internal token.

        Returns:
            QueueTicket: Matching ticket instance.

        Raises:
            Http404: If the ticket does not exist or the token is invalid.
        """
        try:
            return TicketTrackingService.get_ticket_by_token(
                internal_token=self.get_internal_token()
            )
        except QueueTicket.DoesNotExist as exc:
            raise Http404("Ticket not found.") from exc
        except ValueError as exc:
            raise Http404(str(exc)) from exc

    def get_tracking_data(self):
        """
        Returns refreshed tracking data for the current ticket.

        Returns:
            TicketTrackingData: Structured ticket tracking data.
        """
        try:
            return TicketTrackingService.get_tracking_data(
                internal_token=self.get_internal_token(),
                refresh_snapshot=True,
            )
        except QueueTicket.DoesNotExist as exc:
            raise Http404("Ticket not found.") from exc
        except ValueError as exc:
            raise Http404(str(exc)) from exc

    def get_context_data(self, **kwargs):
        """
        Adds ticket and tracking data to the template context.
        """
        context = super().get_context_data(**kwargs)
        ticket = self.get_ticket()
        tracking_data = self.get_tracking_data()

        tracking_relative_url = reverse(
            "mvp_qflow_core:ticket_tracking",
            kwargs={"internal_token": ticket.internal_token},
        )
        tracking_absolute_url = self.request.build_absolute_uri(tracking_relative_url)

        context[self.ticket_context_name] = ticket
        context["tracking_data"] = tracking_data
        context["tracking_url"] = tracking_relative_url
        context["tracking_absolute_url"] = tracking_absolute_url
        context["qr_code_data_uri"] = QRCodeService.build_data_uri(
            value=tracking_absolute_url
        )
        context["can_cancel_ticket"] = TicketTrackingService.can_customer_cancel_ticket(
            ticket=ticket
        )
        context["cancel_ticket_url"] = reverse(
            "mvp_qflow_core:ticket_tracking_cancel",
            kwargs={"internal_token": ticket.internal_token},
        )
        return context


class TicketTrackingDetailView(TicketTrackingMixin, TemplateView):
    """
    Displays customer-facing ticket tracking information.

    This page is intended to show:
    - ticket code
    - current status
    - people ahead
    - estimated wait time
    - service and branch context
    - optional cancellation action
    """
    template_name = "mvp_qflow_core/tracking/detail.html"


class TicketTrackingCancelView(TicketTrackingMixin, FormView):
    """
    Handles customer ticket cancellation from the tracking flow.

    The cancellation is allowed only when the tracking service confirms:
    - QR tracking is enabled for the branch
    - customer cancellation is enabled
    - the ticket status is still cancellable
    """
    template_name = "mvp_qflow_core/tracking/cancel.html"
    form_class = TicketTrackingCancelForm

    def dispatch(self, request, *args, **kwargs):
        """
        Pre-validates that the current ticket can still be cancelled.

        Returns:
            HttpResponse: Redirect or normal response flow.
        """
        ticket = self.get_ticket()

        if not TicketTrackingService.can_customer_cancel_ticket(ticket=ticket):
            messages.error(
                request,
                "This ticket can no longer be cancelled.",
            )
            return redirect(self.get_detail_url())

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        Injects the target ticket into the cancellation form.
        """
        kwargs = super().get_form_kwargs()
        kwargs["ticket"] = self.get_ticket()
        return kwargs

    def form_valid(self, form):
        """
        Executes customer ticket cancellation and redirects back
        to the tracking detail page.

        Args:
            form (TicketTrackingCancelForm): Valid confirmation form.

        Returns:
            HttpResponseRedirect: Redirect to tracking detail page.
        """
        try:
            result = TicketTrackingService.cancel_ticket_by_customer(
                internal_token=self.get_internal_token()
            )

            messages.success(
                self.request,
                result.message,
            )

            return redirect(self.get_success_url())

        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

    def get_success_url(self) -> str:
        """
        Returns the tracking detail page URL after successful cancellation.
        """
        return self.get_detail_url()

    def get_detail_url(self) -> str:
        """
        Returns the tracking detail page URL for the current token.
        """
        return reverse(
            "mvp_qflow_core:ticket_tracking",
            kwargs={"internal_token": self.get_internal_token()},
        )