"""
Database models for the Gift Profile MVP.

This module defines the core data structure for the gift platform:
- GiftEvent: A public shareable gift profile or event.
- GiftPreference: Personal preferences linked to a gift event.
- GiftItem: Gift ideas or products added to an event.
- GiftReservation: Silent reservations made by guests.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .utils import generate_event_token


class GiftEvent(models.Model):
    """
    Represents a shareable gift profile or event.

    A GiftEvent works as the main public page that users can share with guests.
    It contains the event information, owner details, and a unique token used
    to generate the public URL.
    """

    title = models.CharField(
        max_length=150,
        help_text="Public title for the gift event or profile.",
    )
    owner_name = models.CharField(
        max_length=120,
        help_text="Name of the person who will receive the gifts.",
    )
    owner_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Optional email address of the gift event owner.",
    )
    description = models.TextField(
        blank=True,
        help_text="Short description or message for guests.",
    )
    event_date = models.DateField(
        blank=True,
        null=True,
        help_text="Optional date for the celebration or event.",
    )
    video = models.FileField(
        upload_to="gifts/events/videos/%Y/%m/",
        blank=True,
        null=True,
        help_text="Optional welcome video for guests (stored in media).",
    )
    token_url = models.CharField(
        max_length=80,
        unique=True,
        editable=False,
        help_text="Unique public token used to access the shared gift profile.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Controls whether the public gift profile is active.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the gift event was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time when the gift event was last updated.",
    )

    class Meta:
        verbose_name = "Gift Event"
        verbose_name_plural = "Gift Events"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """
        Automatically generate a unique public token before saving.

        The token is only generated when the GiftEvent is created for the
        first time and no token has been assigned yet.
        """
        if not self.token_url:
            self.token_url = generate_event_token()

        super().save(*args, **kwargs)

    def __str__(self):
        """
        Return a readable representation of the gift event.
        """
        return f"{self.title} - {self.owner_name}"

class GiftPreference(models.Model):
    """
    Stores personal preferences related to a gift event.

    Preferences can include clothing sizes, favorite colors, preferred brands,
    interests, things to avoid, allergies, or any useful information that helps
    guests choose a better gift.
    """
    
    PREFERENCE_TYPE_CHOICES = (
        ("likes", _("Likes")),
        ("dislikes", _("Dislikes")),
        ("sizes", _("Sizes")),
        ("colors", _("Colors")),
        ("brands", _("Brands")),
        ("interests", _("Interests")),
        ("avoid", _("Things to Avoid")),
        ("other", _("Other")),
    )

    gift_event = models.ForeignKey(
        "GiftEvent", # Ajustado como string por si acaso, o déjalo igual si ya está importado arriba
        on_delete=models.CASCADE,
        related_name="preferences",
        help_text="Gift event associated with this preference.",
    )
    preference_type = models.CharField(
        max_length=30,
        choices=PREFERENCE_TYPE_CHOICES,
        default="likes",
        help_text="Type of preference being stored.",
    )
    title = models.CharField(
        max_length=120,
        help_text="Short label for the preference.",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed preference information.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the preference was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time when the preference was last updated.",
    )
    class Meta:
        verbose_name = _("Gift Preference")
        verbose_name_plural = _("Gift Preferences")
        ordering = ["preference_type", "title"]

    def __str__(self):
        """
        Return a readable representation of the preference.
        """
        return f"{self.get_preference_type_display()} - {self.title}"

class GiftItem(models.Model):
    """
    Represents a gift idea or product inside a gift event.

    A GiftItem can be a specific product with a URL or a more general idea,
    such as a category, experience, brand, or type of gift.
    """

    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    )

    STATUS_CHOICES = (
        ("available", "Available"),
        ("reserved", "Reserved"),
        ("received", "Received"),
        ("inactive", "Inactive"),
    )

    gift_event = models.ForeignKey(
        GiftEvent,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Gift event associated with this gift item.",
    )
    name = models.CharField(
        max_length=150,
        help_text="Name or short description of the gift idea.",
    )
    description = models.TextField(
        blank=True,
        help_text="Additional details about the gift idea.",
    )
    product_url = models.URLField(
        blank=True,
        help_text="Optional external URL for a specific product.",
    )
    image = models.ImageField(
        upload_to="gifts/items/%Y/%m/",
        blank=True,
        null=True,
        help_text="Optional uploaded image for the gift item.",
    )
    estimated_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Optional estimated price for the gift item.",
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
        help_text="Priority level assigned by the gift event owner.",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available",
        help_text="Current status of the gift item.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the gift item was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time when the gift item was last updated.",
    )

    class Meta:
        verbose_name = "Gift Item"
        verbose_name_plural = "Gift Items"
        ordering = ["-created_at"]

    def __str__(self):
        """
        Return a readable representation of the gift item.
        """
        return self.name

class GiftReservation(models.Model):
    """
    Represents a silent reservation made by a guest.

    Guests can reserve a gift item to avoid duplicate gifts. The reservation
    can be made without requiring the guest to create an account.
    """

    gift_item = models.OneToOneField(
        GiftItem,
        on_delete=models.CASCADE,
        related_name="reservation",
        help_text="Gift item reserved by the guest.",
    )
    guest_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional name of the guest making the reservation.",
    )
    guest_email = models.EmailField(
        blank=True,
        help_text="Optional email of the guest making the reservation.",
    )
    message = models.TextField(
        blank=True,
        help_text="Optional private note from the guest.",
    )
    reserved_at = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when the gift item was reserved.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Controls whether the reservation is currently active.",
    )

    class Meta:
        verbose_name = "Gift Reservation"
        verbose_name_plural = "Gift Reservations"
        ordering = ["-reserved_at"]

    def __str__(self):
        """
        Return a readable representation of the reservation.
        """
        return f"Reservation for {self.gift_item.name}"
    
class WaitlistLead(models.Model):
    """
    Stores email addresses of users interested in early access for various MVPs.
    Allows segmentation via the project_name field.
    """
    email = models.EmailField()
    project_name = models.CharField(
        max_length=50,
        default="gifts",
        help_text="The code name identifier of the MVP project (e.g., 'gifts')."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        # Prevents duplicate signups for the same exact project
        unique_together = ("email", "project_name")

    def __str__(self):
        return f"[{self.project_name.upper()}] {self.email}"

