from rest_framework.viewsets import ModelViewSet

from api.v1.users.serializers import UserCreateSerializer, \
    TelegramSettingsSerializer, UserDetailSerializer
from users.models import User


class UserViewSet(ModelViewSet):
    """CRUD for users."""

    queryset = User.objects.select_related('telegram_settings').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserDetailSerializer


class TelegramSettingsViewSet(ModelViewSet):
    """CRUD for Telegram settings."""

    queryset = User.objects.select_related('telegram_settings').all()
    serializer_class = TelegramSettingsSerializer

