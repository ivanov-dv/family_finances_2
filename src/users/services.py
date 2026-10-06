from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from transactions.models import Space
from transactions.services import SpaceService

from .models import CoreSettings, User


def ensure_core_settings(user: User) -> CoreSettings:
    """Вернуть CoreSettings пользователя, создав их при отсутствии.

    У пользователей, созданных мимо регистрации (createsuperuser, shell), настроек нет,
    а страницы приложения обращаются к user.core_settings напрямую и падают с 500.
    Берём первое собственное пространство пользователя либо создаём пространство
    по умолчанию (как при регистрации).
    """
    try:
        return user.core_settings
    except ObjectDoesNotExist:
        pass
    space = Space.objects.filter(user=user).order_by('pk').first()
    if space is None:
        space, _ = Space.objects.get_or_create(user=user, name=SpaceService.default_name(user.username))
    now = timezone.localtime()
    core, _ = CoreSettings.objects.get_or_create(
        user=user,
        defaults={'current_space': space, 'current_month': now.month, 'current_year': now.year},
    )
    return core
