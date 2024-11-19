from rest_framework.generics import get_object_or_404
from rest_framework.mixins import UpdateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from api.v1.users.serializers import (
    UserCreateSerializer,
    TelegramSettingsSerializer,
    UserDetailSerializer,
    CoreSettingsSerializer
)
from users.models import User


class UserViewSet(ModelViewSet):
    """CRUD for users."""

    queryset = User.objects.select_related('telegram_settings').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserDetailSerializer


class CoreSettingsViewSet(
    ListModelMixin,
    UpdateModelMixin,
    GenericViewSet
):
    """Update user settings."""

    serializer_class = CoreSettingsSerializer

    def get_queryset(self):
        return get_object_or_404(User, pk=self.kwargs['user_id']).core_settings

    def get_object(self):
        return get_object_or_404(
            User,
            pk=self.kwargs['user_id']
        ).core_settings

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset())
        return Response(serializer.data)


class TelegramSettingsViewSet(
    ListModelMixin,
    UpdateModelMixin,
    GenericViewSet
):
    """Update telegram settings."""

    serializer_class = TelegramSettingsSerializer

    def get_queryset(self):
        return get_object_or_404(
            User,
            pk=self.kwargs['user_id']
        ).telegram_settings

    def get_object(self):
        return get_object_or_404(
            User,
            pk=self.kwargs['user_id']
        ).telegram_settings

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset())
        return Response(serializer.data)
