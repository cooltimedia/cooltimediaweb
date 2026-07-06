"""
Admin configuration for the Gifts MVP.

Registers the core models so they can be managed from the Django admin panel.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    GiftEvent,
    GiftPreference,
    GiftItem,
    GiftReservation,
    WaitlistLead,
)


class GiftPreferenceInline(admin.TabularInline):
    """
    Inline editor for gift preferences inside a GiftEvent.
    """

    model = GiftPreference
    extra = 1


class GiftItemInline(admin.TabularInline):
    """
    Inline editor for gift items inside a GiftEvent.
    """

    model = GiftItem
    extra = 1


@admin.register(GiftEvent)
class GiftEventAdmin(admin.ModelAdmin):
    """
    Admin configuration for GiftEvent.
    """

    list_display = (
        "title",
        "owner_name",
        "event_date",
        "is_active",
        "created_at",
        "view_qr_thumbnail",
    )
    list_filter = (
        "is_active",
        "event_date",
        "created_at",
    )
    search_fields = (
        "title",
        "owner_name",
        "owner_email",
        "token_url",
    )
    readonly_fields = (
        "token_url",
        "display_qr_code",
        "created_at",
        "updated_at",
    )
    fields = (
        "title",
        "owner_name",
        "owner_email",
        "description",
        "event_date",
        "video",
        "is_active",
        "token_url",
        "display_qr_code",
        "created_at",
        "updated_at",
    )
    inlines = [
        GiftPreferenceInline,
        GiftItemInline,
    ]

    def display_qr_code(self, obj):
        """
        Renders the dynamic QR code image inside the individual event edit page.
        """
        if obj.token_url and obj.is_active:
            # Dynamically resolve the URL pointing to the app's QR view
            qr_url = reverse("gifts:event_qr", kwargs={"token_url": obj.token_url})
            return mark_safe(
                f'<img src="{qr_url}" width="160" height="160" '
                f'style="border: 1px solid #e2e8f0; padding: 6px; border-radius: 12px; background: #fff;" />'
            )
        return "QR code unavailable (Event is inactive or missing token_url)"

    display_qr_code.short_description = "Event QR Code Preview"

    def view_qr_thumbnail(self, obj):
        """
        Renders a mini micro-thumbnail directly in the general records list table.
        """
        if obj.token_url and obj.is_active:
            qr_url = reverse("gifts:event_qr", kwargs={"token_url": obj.token_url})
            return mark_safe(
                f'<img src="{qr_url}" width="36" height="36" '
                f'style="border-radius: 6px; border: 1px solid #cbd5e1;" />'
            )
        return "N/A"

    view_qr_thumbnail.short_description = "QR Code"


@admin.register(GiftPreference)
class GiftPreferenceAdmin(admin.ModelAdmin):
    """
    Admin configuration for GiftPreference.
    """

    list_display = (
        "title",
        "gift_event",
        "preference_type",
        "created_at",
    )
    list_filter = (
        "preference_type",
        "created_at",
    )
    search_fields = (
        "title",
        "description",
        "gift_event__title",
        "gift_event__owner_name",
    )


@admin.register(GiftItem)
class GiftItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for GiftItem.
    """

    list_display = (
        "name",
        "gift_event",
        "estimated_price",
        "priority",
        "status",
        "created_at",
    )
    list_filter = (
        "priority",
        "status",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "gift_event__title",
        "gift_event__owner_name",
    )


@admin.register(GiftReservation)
class GiftReservationAdmin(admin.ModelAdmin):
    """
    Admin configuration for GiftReservation.
    """

    list_display = (
        "gift_item",
        "guest_name",
        "guest_email",
        "reserved_at",
        "is_active",
    )
    list_filter = (
        "is_active",
        "reserved_at",
    )
    search_fields = (
        "gift_item__name",
        "guest_name",
        "guest_email",
    )


@admin.register(WaitlistLead)
class WaitlistLeadAdmin(admin.ModelAdmin):
    """
    Admin layout for managing multi-project MVP waitlist signups.
    """
    # Columns displayed in the main admin table
    list_display = ("email", "project_name", "created_at")
    
    # Crucial sidebar filter: allows you to segment leads by clicking "gifts" or other projects
    list_filter = ("project_name", "created_at")
    
    # Smart search to quickly find emails
    search_fields = ("email", "project_name")
    
    # Reverse chronological order, newest records first
    ordering = ("-created_at",)