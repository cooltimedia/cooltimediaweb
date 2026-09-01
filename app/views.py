"""Project-level views for LinGift."""

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.sitemaps.views import sitemap as django_sitemap
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe

from .sitemaps import MultilingualWagtailSitemap

@require_POST
def set_language(request):
    """Store the selected language and redirect to its exact localized URL."""

    next_url = request.POST.get("next", "/")

    is_safe_url = url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )

    if not is_safe_url:
        next_url = "/"

    response = HttpResponseRedirect(next_url)
    language_code = request.POST.get("language")

    supported_languages = {
        code for code, _language_name in settings.LANGUAGES
    }

    if language_code in supported_languages:
        response.set_cookie(
            key=settings.LANGUAGE_COOKIE_NAME,
            value=language_code,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
            secure=settings.LANGUAGE_COOKIE_SECURE,
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        )

    return response

def multilingual_sitemap(request):
    """Serve the sitemap for all published Wagtail locales."""

    sitemaps = {
        "pages": MultilingualWagtailSitemap(request),
    }

    return django_sitemap(
        request,
        sitemaps,
    )

@require_safe
def robots_txt(request):
    """Serve crawler instructions for the LinGift website."""

    sitemap_url = request.build_absolute_uri(
        reverse("sitemap")
    )

    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /django-admin/",
        "Disallow: /documents/",
        "Disallow: /i18n/",
        "Disallow: /language/",
        f"Sitemap: {sitemap_url}",
    ]

    return HttpResponse(
        "\n".join(lines) + "\n",
        content_type="text/plain; charset=utf-8",
    )