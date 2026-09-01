"""Sitemap definitions for LinGift."""

from django.contrib.sitemaps import Sitemap
from django.db.models import Q
from django.utils import translation

from wagtail.models import Page, Site


class MultilingualWagtailSitemap(Sitemap):
    """Generate sitemap entries for every published Wagtail locale."""

    def __init__(self, request):
        """Store the request used to resolve localized page URLs."""

        self.request = request

    def items(self):
        """Return public pages from every translated site tree."""

        site = Site.find_for_request(self.request)

        if site is None:
            return Page.objects.none()

        translated_roots = (
            site.root_page
            .get_translations(inclusive=True)
            .live()
            .public()
        )

        page_filter = Q()

        for root_page in translated_roots:
            page_filter |= Q(path__startswith=root_page.path)

        if not page_filter:
            return Page.objects.none()

        return (
            Page.objects
            .filter(page_filter)
            .live()
            .public()
            .select_related("locale")
            .order_by("path")
            .specific()
        )

    def location(self, page):
        """Return the page URL using its content locale."""

        with translation.override(page.locale.language_code):
            return page.get_url(request=self.request)

    def lastmod(self, page):
        """Return the latest publication date for the page."""

        return page.last_published_at