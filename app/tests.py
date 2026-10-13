from unittest.mock import Mock

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.http import HttpResponse

from app.middleware import DemoRobotsMiddleware
from app.sitemaps import MultilingualWagtailSitemap
from app.views import robots_txt
from base.templatetags.seo_tags import canonical_page_url


@override_settings(WAGTAILADMIN_BASE_URL="https://cooltimedia.com")
class TechnicalSeoTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get(
            "/our-services/django-development/?utm_source=test"
        )

    def test_sitemap_forces_https(self):
        sitemap = MultilingualWagtailSitemap(self.request)

        self.assertEqual(sitemap.protocol, "https")

    def test_robots_uses_canonical_https_sitemap(self):
        response = robots_txt(self.request)
        body = response.content.decode()

        self.assertIn(
            "Sitemap: https://cooltimedia.com/sitemap.xml",
            body,
        )
        self.assertNotIn("Sitemap: http://", body)

    def test_canonical_page_url_uses_https_and_drops_query_string(self):
        page = Mock()
        page.get_url.return_value = (
            "http://example.test/our-services/django-development/?draft=1"
        )

        canonical_url = canonical_page_url(
            {"request": self.request},
            page,
        )

        self.assertEqual(
            canonical_url,
            "https://cooltimedia.com/our-services/django-development/",
        )

    def test_demo_routes_emit_x_robots_tag(self):
        middleware = DemoRobotsMiddleware(
            lambda request: HttpResponse("demo")
        )

        response = middleware(
            self.request_factory.get("/gifts/share/example/")
        )

        self.assertEqual(
            response.headers["X-Robots-Tag"],
            "noindex, follow, noarchive",
        )

