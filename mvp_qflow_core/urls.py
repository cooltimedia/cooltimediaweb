"""
URL configuration for the QFlow MVP application.

This module keeps the QFlow routes isolated from Wagtail page routing
by mounting the entire app under its own URL prefix.
"""

from django.urls import path

from mvp_qflow_core.views.kiosk_views import (
    KioskHomeView,
    KioskPrintTicketView,
    KioskTicketCreatedView,
)
from mvp_qflow_core.views.public_views import (
    PublicQueueDisplayView,
    PublicQueueSummaryJsonView,
)
from mvp_qflow_core.views.staff_views import (
    StaffCallNextTicketView,
    StaffCancelTicketView,
    StaffDashboardView,
    StaffFinishServiceView,
    StaffMarkMissedTicketView,
    StaffNoResponseView,
    StaffRecallTicketView,
    StaffStartServiceView,
)
from mvp_qflow_core.views.tracking_views import (
    TicketTrackingCancelView,
    TicketTrackingDetailView,
)
from mvp_qflow_core.views.print_views import TicketPrintEventView

app_name = "mvp_qflow_core"

urlpatterns = [
    # ---------------------------------------------------------
    # Kiosk flow
    # ---------------------------------------------------------
    path(
        "kiosk/<slug:branch_slug>/",
        KioskHomeView.as_view(),
        name="kiosk_home",
    ),
    path(
        "kiosk/<slug:branch_slug>/ticket/<str:internal_token>/",
        KioskTicketCreatedView.as_view(),
        name="kiosk_ticket_created",
    ),
    path(
        "kiosk/<slug:branch_slug>/print/<str:internal_token>/",
        KioskPrintTicketView.as_view(),
        name="kiosk_print_ticket",
    ),

    # ---------------------------------------------------------
    # Ticket Print
    # ---------------------------------------------------------
    path(
        "print/event/",
        TicketPrintEventView.as_view(),
        name="ticket_print_event",
    ),

    # ---------------------------------------------------------
    # Ticket tracking flow
    # ---------------------------------------------------------

    path(
        "track/<str:internal_token>/",
        TicketTrackingDetailView.as_view(),
        name="ticket_tracking",
    ),
    path(
        "track/<str:internal_token>/cancel/",
        TicketTrackingCancelView.as_view(),
        name="ticket_tracking_cancel",
    ),

    # ---------------------------------------------------------
    # Staff dashboard flow
    # ---------------------------------------------------------

    path(
        "staff/<slug:branch_slug>/",
        StaffDashboardView.as_view(),
        name="staff_dashboard",
    ),
    path(
        "staff/<slug:branch_slug>/service/<int:service_id>/call-next/",
        StaffCallNextTicketView.as_view(),
        name="staff_call_next_ticket",
    ),
    path(
        "staff/<slug:branch_slug>/ticket/<int:ticket_id>/recall/",
        StaffRecallTicketView.as_view(),
        name="staff_recall_ticket",
    ),
    path(
        "staff/<slug:branch_slug>/ticket/<int:ticket_id>/no-response/",
        StaffNoResponseView.as_view(),
        name="staff_no_response_ticket",
    ),
    path(
        "staff/<slug:branch_slug>/ticket/<int:ticket_id>/start-service/",
        StaffStartServiceView.as_view(),
        name="staff_start_service",
    ),
    path(
        "staff/<slug:branch_slug>/ticket/<int:ticket_id>/finish-service/",
        StaffFinishServiceView.as_view(),
        name="staff_finish_service",
    ),
    path(
        "staff/<slug:branch_slug>/ticket/<int:ticket_id>/cancel/",
        StaffCancelTicketView.as_view(),
        name="staff_cancel_ticket",
    ),
    path(
        "staff/<slug:branch_slug>/ticket/<int:ticket_id>/mark-missed/",
        StaffMarkMissedTicketView.as_view(),
        name="staff_mark_missed_ticket",
    ),

    # ---------------------------------------------------------
    # Public display flow
    # ---------------------------------------------------------
    
    path(
        "public/<slug:branch_slug>/",
        PublicQueueDisplayView.as_view(),
        name="public_display",
    ),
    path(
        "public/<slug:branch_slug>/summary.json",
        PublicQueueSummaryJsonView.as_view(),
        name="public_display_summary_json",
    ),

]