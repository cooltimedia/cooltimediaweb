"""
Print-related views for the QFlow MVP application.

These views support browser-based print flow telemetry and operator feedback.
"""

import json

from django.http import Http404, JsonResponse
from django.views import View

from mvp_qflow_core.models import QueueTicket
from mvp_qflow_core.services.ticket_print_service import TicketPrintService


class TicketPrintEventView(View):
    """
    Receives print-flow events from the kiosk UI and writes them to logs.
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        """
        Accepts a JSON payload with:
        - internal_token
        - event
        - details (optional)
        """
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse(
                {"success": False, "message": "Invalid JSON payload."},
                status=400,
            )

        internal_token = (payload.get("internal_token") or "").strip()
        event = (payload.get("event") or "").strip()
        details = payload.get("details") or {}

        if not internal_token:
            return JsonResponse(
                {"success": False, "message": "internal_token is required."},
                status=400,
            )

        if not event:
            return JsonResponse(
                {"success": False, "message": "event is required."},
                status=400,
            )

        try:
            ticket = QueueTicket.objects.select_related(
                "branch",
                "service_type",
                "assigned_agent",
            ).get(internal_token=internal_token)
        except QueueTicket.DoesNotExist as exc:
            raise Http404("Ticket not found.") from exc

        try:
            TicketPrintService.log_print_event(
                ticket=ticket,
                event=event,
                user=request.user if request.user.is_authenticated else None,
                payload={
                    "source": "kiosk_ticket_created_page",
                    "details": details,
                },
            )
        except ValueError as exc:
            return JsonResponse(
                {"success": False, "message": str(exc)},
                status=400,
            )

        return JsonResponse({"success": True})