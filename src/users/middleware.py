from .services import ensure_core_settings


class EnsureCoreSettingsMiddleware:
    """Гарантирует, что у вошедшего пользователя есть CoreSettings (иначе страницы падают с 500)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            ensure_core_settings(request.user)
        return self.get_response(request)
