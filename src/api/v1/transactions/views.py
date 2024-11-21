from django.db import transaction, IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from transactions.models import Summary, Basename, LinkedUserToBasename
from users.models import User
from .serializers import TransactionCreateSerializer, GroupCreateSerializer, \
    GroupDetailSerializer, SummarySerializer, TransactionDetailSerializer, \
    BasenameSerializer, LinkUserToBasenameSerializer


class TransactionViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    GenericViewSet
):
    """Отображение и создание для transactions."""

    serializer_class = TransactionCreateSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('period_month', 'period_year', 'basename__id')
    search_fields = ('^group_name',)

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        return self.get_user().transactions

    def get_serializer_class(self):
        if self.action == 'create':
            return TransactionCreateSerializer
        return TransactionDetailSerializer

    def perform_create(self, serializer):
        user = self.get_user()
        with transaction.atomic():
            serializer.save(
                author=user,
                basename=user.core_settings.current_basename,
                period_month=user.core_settings.current_month,
                period_year=user.core_settings.current_year
            )
            summary = Summary.objects.get(
                basename=user.core_settings.current_basename,
                period_month=user.core_settings.current_month,
                period_year=user.core_settings.current_year,
                type_transaction=serializer.validated_data['type_transaction'],
                group_name=serializer.validated_data['group_name']
            )
            summary.fact_value += serializer.validated_data['value_transaction']
            summary.save()


class GroupViewSet(ModelViewSet):
    """CRUD для group."""

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        return Summary.objects.filter(basename__user_id=self.kwargs['user_id'])

    def get_serializer_class(self):
        if self.action == 'create':
            return GroupCreateSerializer
        return GroupDetailSerializer

    def perform_create(self, serializer):
        user = self.get_user()
        serializer.save(
            basename=user.core_settings.current_basename
        )


class SummaryViewSet(
    ListModelMixin,
    GenericViewSet
):
    """Просмотр Summary."""

    serializer_class = SummarySerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('group_name', 'type_transaction')
    search_fields = ('^group_name',)

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        user = self.get_user()
        return Summary.objects.filter(
            basename=user.core_settings.current_basename,
            period_month=user.core_settings.current_month,
            period_year=user.core_settings.current_year
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        user = self.get_user()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'username': user.username,
                'period_month': user.core_settings.current_month,
                'period_year': user.core_settings.current_year,
                'current_basename_id': user.core_settings.current_basename.id,
                'summary': serializer.data
            }
        )


class BasenameViewSet(ModelViewSet):
    """CRUD для Basename."""

    serializer_class = BasenameSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^basename',)

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        return Basename.objects.filter(user_id=self.kwargs['user_id'])

    def perform_create(self, serializer):
        serializer.save(user=self.get_user())

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        user = self.get_user()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'owner_id': user.id,
                'owner_username': user.username,
                'basenames': serializer.data
            }
        )

    @action(detail=True, methods=['post'], url_path='link_user')
    def link_user(self, request, user_id, pk=None):
        basename = self.get_object()
        if basename.user.id != int(user_id):
            return Response(
                {'detail': f'У пользователя id {user_id} нет базы с id {pk}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = LinkUserToBasenameSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data.get('id') == int(user_id):
                return Response(
                    {'detail': 'Нельзя самого себя подключить к базе.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            linked_user = get_object_or_404(
                User,
                pk=serializer.validated_data.get('id')
            )
            linked = LinkedUserToBasename(
                basename=basename,
                linked_user=linked_user
            )
            try:
                linked.save()
            except IntegrityError as e:
                return Response(
                    {'detail': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {'status': f'Пользователь {linked_user.username} '
                           f'(id {linked_user.id}) '
                           f'подключен к базе {basename.basename} '
                           f'(id {basename.id}) пользователя '
                           f'{basename.user.username} '
                           f'(id {basename.user.id}).'}
            )
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='unlink_user')
    def unlink_user(self, request, user_id, pk=None):
        basename = self.get_object()
        if basename.user.id != int(user_id):
            return Response(
                {'detail': f'У пользователя id {user_id} нет базы с id {pk}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = LinkUserToBasenameSerializer(data=request.data)
        if serializer.is_valid():
            linked_user = get_object_or_404(
                User,
                pk=serializer.validated_data.get('id')
            )
            link_object = get_object_or_404(
                LinkedUserToBasename,
                basename=basename,
                linked_user=linked_user
            )
            link_object.delete()
            return Response(
                {'status': f'Пользователь {linked_user.username} '
                           f'(id {linked_user.id}) '
                           f'отключен от базы {basename.basename} '
                           f'(id {basename.id}) пользователя '
                           f'{basename.user.username} '
                           f'(id {basename.user.id}).'}
            )
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
