from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import UpdateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from api.v1.permissions import IsSelfUser
from api.v1.users.filters import UserFilter
from api.v1.users.serializers import (
    UserCreateSerializer,
    TelegramSettingsSerializer,
    UserDetailSerializer,
    CoreSettingsSerializer,
    CoreSettingsUpdateSerializer
)
from users.models import User, CoreSettings


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
    permission_classes = (IsAdminUser,)

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


class ProfileAPIView(APIView):
    """Отображение и редактирование профиля пользователя."""

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        serializer = UserDetailSerializer(self.request.user)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = UserDetailSerializer(
            self.request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CoreSettingsAPIView(APIView):
    """Отображение и редактирование core настроек пользователя."""

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        serializer = CoreSettingsSerializer(self.request.user.core_settings)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = CoreSettingsUpdateSerializer(
            self.request.user.core_settings,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TelegramSettingsAPIView(APIView):
    """Отображение и редактирование telegram настроек пользователя."""

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        serializer = TelegramSettingsSerializer(self.request.user.telegram_settings)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = TelegramSettingsSerializer(
            self.request.user.telegram_settings,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        serializer = TelegramSettingsSerializer(
            self.request.user.telegram_settings,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
