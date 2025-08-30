import django_filters
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFilter(django_filters.FilterSet):
    """Фильтр для пользователей."""

    username = django_filters.CharFilter(
        field_name='username',
        lookup_expr='iexact'
    )
    email = django_filters.CharFilter(
        field_name='email',
        lookup_expr='iexact'
    )
    id_telegram = django_filters.CharFilter(
        field_name='telegram_settings__id_telegram',
        lookup_expr='iexact'
    )
    telegram_only = django_filters.CharFilter(
        field_name='telegram_settings__telegram_only',
        lookup_expr='iexact'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'id_telegram', 'telegram_only')
