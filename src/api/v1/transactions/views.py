from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from transactions.models import Summary
from users.models import User
from .serializers import TransactionCreateSerializer, GroupCreateSerializer, \
    GroupDetailSerializer, SummarySerializer, TransactionDetailSerializer


class TransactionViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    GenericViewSet
):
    """CRUD for transactions."""

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
    """CRUD for group."""

    serializer_class = GroupCreateSerializer

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
