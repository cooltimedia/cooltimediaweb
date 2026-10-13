"""Template tags for canonical and localized public URLs."""

from urllib.parse import urljoin, urlsplit

from django import template
from django.conf import settings


register = template.Library()


def _public_url(raw_url):
    """Return an HTTPS URL on the configured canonical site origin."""

    base_url = settings.WAGTAILADMIN_BASE_URL.rstrip("/") + "/"
    parsed_url = urlsplit(raw_url or "/")
    relative_path = parsed_url.path.lstrip("/")

    return urljoin(base_url, relative_path)


@register.simple_tag
def public_absolute_url(raw_url):
    """Build an absolute public URL for a local page or media path."""

    return _public_url(raw_url)


@register.simple_tag(takes_context=True)
def canonical_page_url(context, page=None):
    """Build a query-free canonical URL for a Wagtail page or request."""

    request = context.get("request")

    if page is not None:
        raw_url = page.get_url(request=request) or page.url
    elif request is not None:
        raw_url = request.path
    else:
        raw_url = "/"

    return _public_url(raw_url)
