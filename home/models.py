from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

class HomePage(Page):
    """Main home page."""
    template = "home/home_page.html"
    
    # We added an introduction field to make it more dynamic
    intro = RichTextField(blank=True, help_text="Texto de bienvenida")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    # Limit which pages can be created below the Home page
    subpage_types = ['home.ServicePage', 'home.ContactPage']

class ServicePage(Page):
    """Page to detail individual services."""
    template = "home/service_page.html"
    description = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('description'),
    ]

    # This page shouldn't have children
    subpage_types = []

class ContactPage(Page):
    """Contact Page."""
    template = "home/contact_page.html"
    address = models.CharField(max_length=255, blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel('address'),
    ]

    # Prevent the creation of sub-pages under the contact page
    subpage_types = []