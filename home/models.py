"""
Home Model
Description: Core models for managing main pages.
Author: Cooltimedia
"""

from django.db import models
from wagtail.models import Page, Orderable
from wagtail.fields import RichTextField, StreamField
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images import get_image_model_string
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel


class HomePageClientLogo(Orderable):
    """An organization logo displayed in the Home page success section."""

    page = ParentalKey(
        "home.HomePage",
        on_delete=models.CASCADE,
        related_name="client_logos",
    )
    organization_name = models.CharField(
        max_length=120,
        verbose_name="Nombre de la organización",
    )
    logo = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name="Logo",
    )

    panels = [
        FieldPanel("organization_name"),
        FieldPanel("logo"),
    ]

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Logo de organización"
        verbose_name_plural = "Logos de organizaciones"


class HomePage(Page):
    """Main home page."""

    template = "home/home_page.html"

    intro = RichTextField(
        blank=True,
        help_text="Texto de bienvenida",
    )

    about_image_1 = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Imagen principal de la sección Sobre mí",
        help_text="Imagen horizontal principal.",
    )

    about_image_2 = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Segunda imagen de la sección Sobre mí",
        help_text="Por ejemplo: premio, presentación o conferencia.",
    )

    about_image_3 = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Tercera imagen de la sección Sobre mí",
        help_text="Por ejemplo: colaboración o actividad profesional.",
    )

    about_image_4 = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Cuarta imagen de la sección Sobre mí",
        help_text="Por ejemplo: colaboración o actividad profesional.",
    )

    about_image_5 = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Quinta imagen de la sección Sobre mí",
        help_text="Por ejemplo: colaboración o actividad profesional.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("about_image_1"),
        FieldPanel("about_image_2"),
        FieldPanel("about_image_3"),
        FieldPanel("about_image_4"),
        FieldPanel("about_image_5"),
        InlinePanel("client_logos", label="Logos de organizaciones"),
    ]

    subpage_types = [
        "home.SolutionsPage",
        "home.ServicesPage",
        "home.ContactPage",
        "home.CorporateSocialResponsibility",
        "blog.BlogIndexPage",
        "home.PrivacyPolicyPage",
        "home.TermsServicePage",
    ]


class PrivacyPolicyPage(Page):
    """
    A page for Privacy Policy.
    """
    template = "home/privacy_policy_page.html"
    body = StreamField([
        ('heading', blocks.CharBlock(form_class="title", label="Heading")),
        ('paragraph', blocks.RichTextBlock(label="Paragraph text")),
        ('image', ImageChooserBlock(label="Featured Image")),
        ('code', blocks.StructBlock([
            ('language', blocks.ChoiceBlock(choices=[
                ('python', 'Python'), 
                ('javascript', 'JavaScript'),
                ('html', 'HTML/Django Template'),
                ('bash', 'Bash/Terminal'),
                ('yaml', 'YAML/Docker'),
            ], label="Programming Language")),
            ('code', blocks.TextBlock(label="Code snippet")),
        ], label="Code Block", icon="code")),
    ], use_json_field=True)
    last_updated = models.DateField(auto_now=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    # Limit to one instance
    parent_page_types = ['home.HomePage']

class TermsServicePage(Page):
    """
    A page for Terms of Service.
    """
    template = "home/terms_service_page.html"
    body = StreamField([
        ('heading', blocks.CharBlock(form_class="title", label="Heading")),
        ('paragraph', blocks.RichTextBlock(label="Paragraph text")),
        ('image', ImageChooserBlock(label="Featured Image")),
        ('code', blocks.StructBlock([
            ('language', blocks.ChoiceBlock(choices=[
                ('python', 'Python'), 
                ('javascript', 'JavaScript'),
                ('html', 'HTML/Django Template'),
                ('bash', 'Bash/Terminal'),
                ('yaml', 'YAML/Docker'),
            ], label="Programming Language")),
            ('code', blocks.TextBlock(label="Code snippet")),
        ], label="Code Block", icon="code")),
    ], use_json_field=True)
    last_updated = models.DateField(auto_now=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    # Limit to one instance
    parent_page_types = ['home.HomePage']

class SolutionsPage(Page):
    """Page to main solutions page."""
    template = "home/solutions/solutions_page.html"
    description = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('description'),
    ]

    # Limit which pages can be created below the Solutions page
    subpage_types = ['home.SmartQueueMVPPage','home.SmartAccountingMVPPage']

class ServicesPage(Page):
    """Main services index page."""
    template = "home/services/services_page.html"

    description = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("description"),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = ["home.ServicePage"]

    max_count = 1

class ServicePage(Page):
    """Individual service landing page."""

    template = "home/services/service_page.html"

    hero_subtitle = models.TextField(blank=True)

    body = StreamField([
        ("heading", blocks.CharBlock(form_class="title", label="Heading")),
        ("paragraph", blocks.RichTextBlock(label="Paragraph text")),
        ("image", ImageChooserBlock(label="Image")),

        ("caption", blocks.RichTextBlock(
            label="Caption / Image credit",
            required=False,
            features=["bold", "italic", "link"],
        )),

        ("cta", blocks.StructBlock([
            ("title", blocks.CharBlock(label="CTA Title")),
            ("text", blocks.TextBlock(label="CTA Text", required=False)),
            ("button_text", blocks.CharBlock(label="Button Text")),
            ("button_url", blocks.URLBlock(label="Button URL")),
        ], label="Call to Action", icon="plus-inverse")),

        ("faq", blocks.StructBlock([
            ("question", blocks.CharBlock(label="Question")),
            ("answer", blocks.RichTextBlock(label="Answer")),
        ], label="FAQ", icon="help")),

        ("code", blocks.StructBlock([
            ("language", blocks.ChoiceBlock(choices=[
                ("python", "Python"),
                ("javascript", "JavaScript"),
                ("html", "HTML/Django Template"),
                ("bash", "Bash/Terminal"),
                ("yaml", "YAML/Docker"),
            ], label="Programming Language")),
            ("code", blocks.TextBlock(label="Code snippet")),
        ], label="Code Block", icon="code")),
    ], use_json_field=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("hero_subtitle"),
        FieldPanel("body"),
    ]

    parent_page_types = ["home.ServicesPage"]
    subpage_types = []

class SmartQueueMVPPage(Page):
    """Page to detail individual solutions (Smart Queue MVP)"""
    template = "home/solutions/lab/smart_queue_mvp_page.html"
    description = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('description'),
    ]

    # This page shouldn't have children
    subpage_types = []

class SmartAccountingMVPPage(Page):
    """Page to detail individual solutions (Smart Accounting MVP)"""
    template = "home/solutions/lab/smart_accounting_mvp_page.html"
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

class CorporateSocialResponsibility(Page):
    """Corporate Social Responsibility."""
    template = "home/crs.html"
    description = RichTextField(blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel('description'),
    ]

    # Prevent the creation of sub-pages under the contact page
    subpage_types = []