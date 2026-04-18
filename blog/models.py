"""
Blog Model
Description: Core models for managing blog posts.
Author: Cooltimedia
Date: April 16, 2026
"""

from django.db import models

# Wagtail core imports
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.images.blocks import ImageChooserBlock
from wagtail.snippets.models import register_snippet

# Wagtail Metadata for SEO (Open Graph, Twitter Cards, etc.)
from wagtailmetadata.models import MetadataPageMixin

@register_snippet
class Author(models.Model):
    """
    A snippet to manage blog authors.
    Centralizing author info helps with Google's E-E-A-T requirements.
    """
    name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True, help_text="Short biography for the post footer")
    image = models.ForeignKey(
        'wagtailimages.Image',
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        related_name='+'
    )
    # Social links for author verification (SEO 2026)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True, verbose_name="X (Twitter) URL")
    instagram_url = models.URLField(blank=True, verbose_name="Instagram URL")

    panels = [
        FieldPanel('name'),
        FieldPanel('job_title'),
        FieldPanel('image'),
        FieldPanel('bio'),
        MultiFieldPanel([
            FieldPanel('linkedin_url'),
            FieldPanel('twitter_url'),
            FieldPanel('instagram_url'),
        ], heading="Social Media Profiles"),
    ]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Author"
        verbose_name_plural = "Authors"

class BlogIndexPage(MetadataPageMixin, Page):
    """
    Index page for the blog. 
    This page lists all the individual blog posts (BlogPage).
    Inherits from MetadataPageMixin to provide enhanced SEO fields.
    """
    intro = models.TextField(blank=True, help_text="Text shown at the top of the blog listing")

    # Content panels for the editor interface
    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    # Combine Wagtail's default promotion panels with MetadataPageMixin panels
    # This allows for custom SEO titles, descriptions, and social media images.
    promote_panels = MetadataPageMixin.promote_panels + Page.promote_panels

    # Limits the types of subpages that can be created under the Index
    parent_page_types = ['home.HomePage'] 
    subpage_types = ['blog.BlogPage']
    
    # Ensures only one instance of the Blog Index can exist in the CMS
    max_count = 1

    class Meta:
        verbose_name = "Blog Index Page"


class BlogPage(MetadataPageMixin, Page):
    """
    Individual blog post page.
    Used for specific articles like "My experience at DjangoCon 2025".
    """
    date = models.DateField("Post date")
    intro = models.CharField(
        max_length=250, 
        help_text="A short summary to be displayed in listings and search results"
    )
    author = models.ForeignKey(
        'blog.Author',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blog_posts'
    )

    # StreamField provides a flexible way to build the post body using different blocks.
    # Essential for technical blogs requiring code snippets and varied layouts.
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

    # Panels to organize the fields in the Wagtail admin sidebar/tabs
    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('author'),
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    # SEO and Social Media panels
    promote_panels = MetadataPageMixin.promote_panels + Page.promote_panels

    # Ensures BlogPages can only be created as children of a BlogIndexPage
    parent_page_types = ['blog.BlogIndexPage']

    class Meta:
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"