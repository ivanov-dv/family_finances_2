from django.db import transaction, IntegrityError
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin
)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from transactions.models import Summary, Space
from users.models import User
from .serializers import (
    TransactionCreateSerializer,
    SummaryDetailSerializer,
    TransactionDetailSerializer,
    LinkUserToSpaceSerializer,
    UnlinkUserToSpaceSerializer,
    SpaceSerializer,
    SummaryCreateSerializer
)


class TransactionViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    GenericViewSet
):
    """Отображение и создание для transactions."""

    serializer_class = TransactionCreateSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('period_month', 'period_year', 'space__id')
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
                space=user.core_settings.current_space,
                period_month=user.core_settings.current_month,
                period_year=user.core_settings.current_year
            )
            summary = Summary.objects.get(
                space=user.core_settings.current_space,
                period_month=user.core_settings.current_month,
                period_year=user.core_settings.current_year,
                type_transaction=serializer.validated_data['type_transaction'],
                group_name=serializer.validated_data['group_name']
            )
            summary.fact_value += serializer.validated_data[
                'value_transaction'
            ]
            summary.save()


class SummaryViewSet(ModelViewSet):
    """Просмотр Summary."""

    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('group_name', 'type_transaction')
    search_fields = ('^group_name',)

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        user = self.get_user()
        return Summary.objects.filter(
            space=user.core_settings.current_space,
            period_month=user.core_settings.current_month,
            period_year=user.core_settings.current_year
        )

    def get_serializer_class(self):
        if self.action in ('create', 'update'):
            return SummaryCreateSerializer
        return SummaryDetailSerializer

    def perform_create(self, serializer):
        try:
            serializer.save(
                space=self.get_user().core_settings.current_space,
                period_month=self.get_user().core_settings.current_month,
                period_year=self.get_user().core_settings.current_year
            )
        except IntegrityError:
            raise ValidationError(
                'Не уникальное имя группы для текущего периода и базы.'
            )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        income_plan = queryset.filter(
            type_transaction='income'
        ).aggregate(Sum('plan_value'))['plan_value__sum']
        income_fact = queryset.filter(
            type_transaction='income'
        ).aggregate(Sum('fact_value'))['fact_value__sum']
        expense_plan = queryset.filter(
            type_transaction='expense'
        ).aggregate(Sum('plan_value'))['plan_value__sum']
        expense_fact = queryset.filter(
            type_transaction='expense'
        ).aggregate(Sum('fact_value'))['fact_value__sum']
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'sum_income_plan': income_plan,
                'sum_income_fact': income_fact,
                'sum_expense_plan': expense_plan,
                'sum_expense_fact': expense_fact,
                'balance_plan': income_plan - expense_plan,
                'balance_fact': income_fact - expense_fact,
                'summary': serializer.data
            }
        )


class SpaceViewSet(ModelViewSet):
    """CRUD для Basename."""

    serializer_class = SpaceSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        return Space.objects.filter(user_id=self.kwargs['user_id'])

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
                'spaces': serializer.data
            }
        )

    @swagger_auto_schema(
        tags=['Подключение/отключение пользователей'],
        operation_description='Подключение пользователя к базе',
        responses={
            status.HTTP_200_OK:
                'Пользователь username '
                '(id 1) подключен к базе '
                'user_base '
                '(id 11) '
                'пользователя username_2 '
                '(id 22).'
        },
        request_body=LinkUserToSpaceSerializer
    )
    @action(detail=True, methods=['post'], url_path='link_user')
    def link_user(self, request, user_id, pk=None):
        serializer = LinkUserToSpaceSerializer(
            data=request.data,
            context={'space_id': pk, 'user_id': int(user_id)}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {
                'status': f'Пользователь {instance.linked_user.username} '
                          f'(id {instance.linked_user.id}) подключен к базе '
                          f'{instance.space.name} '
                          f'(id {instance.space.id}) '
                          f'пользователя {instance.space.user.username} '
                          f'(id {instance.space.user.id}).'
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        tags=['Подключение/отключение пользователей'],
        operation_description='Отключение пользователя от базы',
        responses={
            status.HTTP_200_OK:
                'Пользователь username '
                '(id 1) отключен от базы '
                'user_base '
                '(id 11) '
                'пользователя username_2 '
                '(id 22).'
        },
        request_body=UnlinkUserToSpaceSerializer
    )
    @action(detail=True, methods=['post'], url_path='unlink_user')
    def unlink_user(self, request, user_id, pk=None):
        serializer = UnlinkUserToSpaceSerializer(
            data=request.data,
            context={'space_id': pk, 'user_id': int(user_id)}
        )
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        serializer.delete(vd)
        return Response(
            {
                'status': f'Пользователь {vd['linked_user'].username} '
                          f'(id {vd['linked_user'].id}) отключен от базы '
                          f'{vd['space'].name} '
                          f'(id {vd['space'].id}) '
                          f'пользователя {vd['space'].user.username} '
                          f'(id {vd['space'].user.id}).'
            },
            status=status.HTTP_200_OK
        )
