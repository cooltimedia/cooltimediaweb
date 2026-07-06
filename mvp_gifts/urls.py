# mvp_gifts/urls.py

"""
URL Configuration for the Gifts MVP.

Defines the routing for the main dashboard and the public shared gift profile.
The app allows users to manage their gift preferences and share a unique public
URL with guests, so they can view the gift profile without creating an account.
"""

from django.urls import path

from .views import (
    DashboardView,
    PublicGiftProfileView,
    generate_event_qr,
    add_reservation,
    join_waitlist,
)


app_name = "gifts"


urlpatterns = [
    # Main Interface
    path(
        "dashboard/",
        DashboardView.as_view(),
        name="dashboard",
    ),

    # Public Shared Gift Profile
    path(
        "share/<str:token_url>/",
        PublicGiftProfileView.as_view(),
        name="public_profile",
    ),
    # AJAX / Fetch endpoints
    path(
        "items/<int:item_id>/reserve/", 
        add_reservation, 
        name='reserve_item'
    ),
    path(
        "event/<str:token_url>/qr/",
        generate_event_qr,
        name="event_qr"
    ),
    path(
        "waitlist/join/",
        join_waitlist, 
        name="join_waitlist"
    ),
]