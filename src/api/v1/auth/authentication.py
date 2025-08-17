from django.contrib.auth import get_user_model, settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class TokenAuthentication(BaseAuthentication):
    """
    Класс аутентификации, который проверяет token в заголовке запроса.
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        if auth_header != settings.ACCESS_TOKEN:
            raise AuthenticationFailed('Неправильный токен.')
        try:
            user, created = User.objects.get_or_create(username='admin')
            return user, None
        except Exception as e:
            raise AuthenticationFailed(e)
