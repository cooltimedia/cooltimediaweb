"""
Main URL Configuration for Cooltimedia Project.
Integrates Wagtail CMS with the 'Demo' ecosystem, specifically 
routing the Smart Accounting Automation MVP under the 'demo/' prefix.
"""

from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin
from django.views.static import serve

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),

    # --- Cooltimedia Demo Ecosystem ---
    # Prefixing with 'demo/' allows multiple MVPs to coexist without 
    # interfering with Wagtail's page tree.
    path(
        "demo/smart-accounting/",
        include("mvp_smart_accounting.urls", namespace="mvp_smart_accounting"),
    ),

]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

# Wagtail catch-all (Must always be the last pattern)
urlpatterns = urlpatterns + [
    path("", include(wagtail_urls)),
]
