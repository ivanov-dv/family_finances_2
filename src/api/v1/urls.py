from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

from api.v1.users import views as user_views
from api.v1.transactions import views as transactions_views
from api.v1.export import views as export_views

app_name = 'api_v1'

router_v1 = DefaultRouter()

router_v1.register(
    'users',
    user_views.UserViewSet,
    basename='users'
)
router_v1.register(
    r'transactions',
    transactions_views.TransactionViewSet,
    basename='user_transactions'
)
router_v1.register(
    r'summary',
    transactions_views.SummaryViewSet,
    basename='user_summary'
)
router_v1.register(
    r'spaces',
    transactions_views.SpaceViewSet,
    basename='user_spaces'
)
router_v1.register(
    r'periods',
    transactions_views.PeriodViewSet,
    basename='user_periods'
)

urlpatterns = [

    re_path(r'^auth/', include('djoser.urls.authtoken')),
    re_path(r'^auth/', include('djoser.urls.jwt')),
    re_path(r'^auth/', include('djoser.urls')),

    path('', include(router_v1.urls)),

    path('profile/core-settings/', user_views.CoreSettingsAPIView.as_view(), name="profile-core-settings"),
    path('profile/telegram-settings/', user_views.TelegramSettingsAPIView.as_view(), name="profile-telegram-settings"),
    path('profile/', user_views.ProfileAPIView.as_view(), name='profile'),

    path('export/excel/', export_views.ExportAPIView.as_view()),

]
