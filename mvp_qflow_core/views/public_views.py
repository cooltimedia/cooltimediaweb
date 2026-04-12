"""
Public display views for the QFlow MVP application.

These views handle read-only queue visibility for branch public screens:
- branch public queue display
- optional JSON-style serialized queue summary for future async refresh flows
"""

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from mvp_qflow_core.models import BranchSetting
from mvp_qflow_core.services.queue_metrics_service import QueueMetricsService


class PublicBranchMixin:
    """
    Shared helper mixin for public queue display views.

    Responsibilities:
    - resolve the active branch from URL kwargs
    - centralize branch validation
    - provide consistent branch summary access
    """

    branch_kwarg = "branch_slug"

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

    def get_branch_summary(self):
        """
        Returns the public queue summary for the current branch.

        Returns:
            BranchQueueSummary: Public queue summary object.
        """
        return QueueMetricsService.get_branch_public_queue_summary(
            branch=self.get_branch()
        )


class PublicQueueDisplayView(PublicBranchMixin, TemplateView):
    """
    Displays the branch public queue screen.

    This page is intended for public monitors or TVs inside the branch.
    It should present a clear, read-only overview of all active queues.
    """

    template_name = "mvp_qflow_core/public/display.html"

    def get_context_data(self, **kwargs):
        """
        Adds branch and public queue summary context to the template.
        """
        context = super().get_context_data(**kwargs)
        branch = self.get_branch()
        branch_summary = self.get_branch_summary()

        total_open_tickets = sum(
            service.total_open_tickets for service in branch_summary.services
        )
        total_waiting_tickets = sum(
            service.waiting_tickets for service in branch_summary.services
        )
        total_called_tickets = sum(
            service.called_tickets for service in branch_summary.services
        )
        total_attending_tickets = sum(
            service.attending_tickets for service in branch_summary.services
        )

        context["branch"] = branch
        context["branch_summary"] = branch_summary
        context["page_title"] = f"{branch.name} Public Queue Display"
        context["total_open_tickets"] = total_open_tickets
        context["total_waiting_tickets"] = total_waiting_tickets
        context["total_called_tickets"] = total_called_tickets
        context["total_attending_tickets"] = total_attending_tickets
        return context


class PublicQueueSummaryJsonView(PublicBranchMixin, View):
    """
    Returns a serialized branch public queue summary.

    This endpoint is useful for future automatic refresh behavior
    from JavaScript or lightweight polling.
    """

    def get(self, request, *args, **kwargs):
        """
        Returns the current public queue summary for the branch as JSON.
        """
        branch = self.get_branch()
        serialized_summary = QueueMetricsService.serialize_branch_summary(branch=branch)

        total_open_tickets = sum(
            service["total_open_tickets"] for service in serialized_summary["services"]
        )
        total_waiting_tickets = sum(
            service["waiting_tickets"] for service in serialized_summary["services"]
        )
        total_called_tickets = sum(
            service["called_tickets"] for service in serialized_summary["services"]
        )
        total_attending_tickets = sum(
            service["attending_tickets"] for service in serialized_summary["services"]
        )

        return JsonResponse(
            {
                "branch": {
                    "id": branch.id,
                    "name": branch.name,
                    "slug": branch.slug,
                },
                "summary": serialized_summary,
                "totals": {
                    "open": total_open_tickets,
                    "waiting": total_waiting_tickets,
                    "called": total_called_tickets,
                    "attending": total_attending_tickets,
                },
            }
        )