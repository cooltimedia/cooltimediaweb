"""Project middleware for crawler directives."""


class DemoRobotsMiddleware:
    """Prevent functional demo routes from entering search indexes."""

    demo_prefixes = (
        "/demo/",
        "/gifts/",
        "/es/demo/",
        "/es/gifts/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith(self.demo_prefixes):
            response.headers["X-Robots-Tag"] = (
                "noindex, follow, noarchive"
            )

        return response
