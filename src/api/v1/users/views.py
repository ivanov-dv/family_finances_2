from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import UpdateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from api.v1.users.filters import UserFilter
from api.v1.users.serializers import (
    UserCreateSerializer,
    TelegramSettingsSerializer,
    UserDetailSerializer,
    CoreSettingsSerializer,
    CoreSettingsUpdateSerializer
)
from users.models import User


class UserViewSet(ModelViewSet):
    """CRUD для users."""

    queryset = User.objects.prefetch_related(
        'available_linked_spaces__user',
        'spaces__available_linked_users',
    ).select_related(
        'telegram_settings',
        'core_settings__current_space'
    ).all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UserFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserDetailSerializer

    @action(methods=['GET'], detail=False, url_path='get-id')
    def get_id(self, request):
        id_telegram = request.query_params.get('id_telegram')
        user_id = User.objects.filter(
            telegram_settings__id_telegram=id_telegram
        ).values('id').first()
        if user_id:
            return Response({'user_id': user_id['id']})
        raise NotFound(detail='Пользователь не найден.')


class CoreSettingsViewSet(
    ListModelMixin,
    UpdateModelMixin,
    GenericViewSet
):
    """Отображение и обновление user settings."""

    http_method_names = ('get', 'patch')
    serializer_class = CoreSettingsSerializer

    def get_queryset(self):
        return get_object_or_404(User, pk=self.kwargs['user_id']).core_settings

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return CoreSettingsUpdateSerializer
        return CoreSettingsSerializer

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
    """Отображение и обновление telegram settings."""

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
