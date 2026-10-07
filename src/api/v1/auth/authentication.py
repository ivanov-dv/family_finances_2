import hmac

from django.conf import settings
from django.contrib.auth import get_user_model
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
        # Постоянное время сравнения: по задержке ответа нельзя подбирать токен по символам.
        # Пустой/незаданный ACCESS_TOKEN никого не пускает.
        expected = settings.ACCESS_TOKEN or ''
        if not expected or not hmac.compare_digest(auth_header.encode(), expected.encode()):
            raise AuthenticationFailed('Неправильный токен.')
        try:
            user, created = User.objects.get_or_create(username='admin')
            return user, None
        except Exception as e:
            raise AuthenticationFailed(e)
