"""
Views for the Gifts MVP.

This module contains the class-based views used to manage the main dashboard
and the public shared gift profile.

The dashboard allows users to manage their gift profile, preferences, and gift
items. The public view allows guests to access a shared gift profile using a
unique URL token, without requiring authentication.
"""
import qrcode
from io import BytesIO
from django.http import HttpResponse
from django.urls import reverse
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from .models import GiftEvent, GiftItem, GiftReservation, WaitlistLead

class DashboardView(TemplateView):
    """
    Display the main dashboard for the Gifts MVP.

    This view is intended for users who manage their gift profile, event details,
    personal preferences, and gift items.

    Template:
        gifts/dashboard.html
    """

    template_name = "gifts/dashboard.html"

    def get_context_data(self, **kwargs):
        """
        Retrieve the creator's gift event to populate the dashboard context.
        """
        context = super().get_context_data(**kwargs)
        token_url = self.kwargs.get("token_url")

        # Fetch the event securely
        gift_event = get_object_or_404(
            GiftEvent,
            token_url=token_url,
            is_active=True,
        )

        # Pass the event and its relational data to the dashboard templates
        context["gift_event"] = gift_event
        context["items"] = gift_event.items.all()
        context["preferences"] = gift_event.preferences.all()

        return context


class PublicGiftProfileView(TemplateView):
    """
    Display the public gift profile shared with guests.

    Guests can access this page through a unique token in the URL.
    This view is intended to show the gift profile, preferences, and available
    gift ideas without requiring the guest to create an account.

    URL example:
        /gifts/share/<token_url>/

    Template:
        gifts/public_gift_profile.html
    """

    template_name = "gifts/public_gift_profile.html"

    def get_context_data(self, **kwargs):
        """
        Retrieve the shared gift event and its categorized preferences.
        """
        context = super().get_context_data(**kwargs)

        token_url = self.kwargs.get("token_url")

        gift_event = get_object_or_404(
            GiftEvent,
            token_url=token_url,
            is_active=True,
        )

        current_date = timezone.localdate()
        event_has_passed = (
            gift_event.event_date and gift_event.event_date < current_date
        )

        context["gift_event"] = gift_event
        context["event_has_passed"] = event_has_passed

        # Optimization: If the event has passed, do not load unnecessary items into the context
        if not event_has_passed:
            all_preferences = gift_event.preferences.all()
            context["items"] = gift_event.items.all()

            context["avoid_preferences"] = all_preferences.filter(
                preference_type__in=["dislikes", "avoid"]
            )
            context["love_preferences"] = all_preferences.filter(
                preference_type__in=["likes", "interests"]
            )
            context["spec_preferences"] = all_preferences.filter(
                preference_type__in=["sizes", "colors", "brands", "other"]
            )

        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response


def generate_event_qr(request, token_url):
    """
    Generates a dynamic QR code in memory for a specific gift event.
    
    Constructs the absolute public sharing URL and returns the QR code 
    directly as a PNG image stream.
    """
    # Verify that the active event exists
    gift_event = get_object_or_404(GiftEvent, token_url=token_url, is_active=True)
    
    # 1. Build the absolute public URL (e.g., https://cooltimedia.com/gifts/share/2026...)
    share_url = request.build_absolute_uri(
        reverse('gifts:public_profile', kwargs={'token_url': gift_event.token_url})
    )
    
    # 2. Configure and create the QR code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(share_url)
    qr.make(fit=True)
    
    # Render the QR code using Pillow
    qr_image = qr.make_image(fill_color="#0f172a", back_color="#ffffff") # Matches your dark slate theme
    
    # 3. Save the image to an in-memory stream buffer
    buffer = BytesIO()
    qr_image.save(buffer, format="PNG")
    
    # Return the raw binary stream as a native PNG HTTP response
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@require_POST
def add_reservation(request, item_id):
    """
    API endpoint to silently reserve a gift item.

    Includes concurrency checks (select_for_update) to prevent race conditions 
    if multiple guests try to reserve the same item simultaneously.
    """
    guest_name = request.POST.get("guest_name")

    if not guest_name or not guest_name.strip():
        return JsonResponse(
            {"status": "error", "message": "The guest name field is required."},
            status=400,
        )

    # Use transaction.atomic to ensure database integrity during the lock
    with transaction.atomic():
        # Fetch the item and lock the row using select_for_update()
        gift_item = get_object_or_404(
            GiftItem.objects.select_for_update(),
            id=item_id,
            gift_event__is_active=True
        )

        if (gift_item.gift_event.event_date and gift_item.gift_event.event_date < timezone.localdate()):
            return JsonResponse(
                {
                    "status": "error",
                    "message": "This event has already passed. New reservations are no longer allowed.",
                }
            )

        if gift_item.status != "available":
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Too late! Someone else has already reserved this gift while you were filling out the form.",
                }
            )

        # 1. Create the silent reservation
        GiftReservation.objects.create(
            gift_item=gift_item,
            guest_name=guest_name.strip(),
        )

        # 2. Update status securely
        gift_item.status = "reserved"
        gift_item.save()

    return JsonResponse(
        {"status": "success", "message": "The item has been successfully reserved!"}
    )


@require_POST
def join_waitlist(request):
    """
    API endpoint to securely capture emails for the MVP waitlist segmentation.
    """
    email = request.POST.get("waitlist_email", "").strip()
    project_name = request.POST.get("project_name", "gifts").strip()

    if not email:
        return JsonResponse(
            {"status": "error", "message": "An email address is required."}, 
            status=400
        )

    try:
        # get_or_create automatically handles duplicate prevention safely
        lead, created = WaitlistLead.objects.get_or_create(
            email=email,
            project_name=project_name
        )
        
        return JsonResponse({
            "status": "success", 
            "message": "Thank you! You have been added to our early access list."
        })
        
    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": "Something went wrong. Please try again."}, 
            status=500
        )