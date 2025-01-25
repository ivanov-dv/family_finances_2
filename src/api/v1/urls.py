from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as auth_views

from api.v1.users import views as user_views
from api.v1.transactions import views as transactions_views
from api.v1.export import views as export_views

app_name = 'api_v1'

router_v1 = DefaultRouter()
router_v1.register('users', user_views.UserViewSet, basename='users')
router_v1.register(
    r'profile/core-settings',
    user_views.CoreSettingsViewSet,
    basename='core-settings'
)
router_v1.register(
    r'profile/telegram-settings',
    user_views.TelegramSettingsViewSet,
    basename='telegram-settings'
)
router_v1.register(
    r'profile/transactions',
    transactions_views.TransactionViewSet,
    basename='user_transactions'
)
router_v1.register(
    r'profile/summary',
    transactions_views.SummaryViewSet,
    basename='user_summary'
)
router_v1.register(
    r'profile/spaces',
    transactions_views.SpaceViewSet,
    basename='user_spaces'
)
router_v1.register(
    r'profile/export',
    export_views.ExportView,
    basename='export'
)

urlpatterns = [
    path(
        '',
        include(router_v1.urls)
    ),
    path('profile/', user_views.ProfileAPIView.as_view(), name='profile'),
    re_path(r'^auth/', include('djoser.urls.authtoken')),
    re_path(r'^auth/', include('djoser.urls.jwt')),
]
