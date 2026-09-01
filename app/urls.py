"""
Main URL Configuration for Cooltimedia Project.
Integrates Wagtail CMS with the 'Demo' ecosystem, specifically 
routing the Smart Accounting Automation MVP under the 'demo/' prefix.
"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path, re_path
from django.contrib import admin
from django.views.static import serve

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from .views import (
    multilingual_sitemap,
    robots_txt,
    set_language,
)
from search import views as search_views

urlpatterns = [
    # Language selection must remain outside i18n_patterns.
    path(
        "language/set/",
        set_language,
        name="cooltimedia_set_language",
    ),
    path(
        "robots.txt",
        robots_txt,
        name="robots_txt",
    ),
    path(
        "sitemap.xml",
        multilingual_sitemap,
        name="sitemap",
    ),
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
]

# Wagtail must handle URLs that were not matched by previous patterns.
# Keep this route at the end of the list.
urlpatterns += i18n_patterns(
    # Smart Accounting MVP routes
    path("demo/smart-accounting/", include("mvp_smart_accounting.urls", namespace="mvp_smart_accounting")),
    # QFlow MVP routes
    path("demo/qflow/", include("mvp_qflow_core.urls", namespace="mvp_qflow_core")),
    # Gifts MVP routes
    path("gifts/", include("mvp_gifts.urls")),
    path("search/", search_views.search, name="search"),
    path("", include(wagtail_urls)),
    prefix_default_language=False,
)

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files through Django during development.
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if not settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^static/(?P<path>.*)$",
            serve,
            {"document_root": settings.STATIC_ROOT},
        ),
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]


#Custom Admin Titles
admin.site.site_header = 'Cooltimedia Panamá'
admin.site.index_title = 'Portal Web'
admin.site.site_title = 'Administración del Cooltimedia'