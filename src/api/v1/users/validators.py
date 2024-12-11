from django.conf import settings
from rest_framework.exceptions import ValidationError


def not_allowed_username_validator(username):
    if username in settings.NOT_ALLOWED_USERNAMES:
        raise ValidationError(f'Логин {username} зарезервирован.')
    return username
