from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.v1.users import views as user_views

app_name = 'api_v1'

router_v1 = DefaultRouter()
router_v1.register('users', user_views.UserViewSet, basename='users')
# router_v1.register(
#     r'users/(?P<user_id>\d+)/transactions', views.
#     views.CommentViewSet,
#     basename='post_comments'
# )

urlpatterns = [
    path('', include(router_v1.urls)),
    path(
        'users/<int:user_id>/core-settings/',
        user_views.CoreSettingsViewSet.as_view(
            {'put': 'update', 'get': 'list', 'patch': 'partial_update'}
        )
    ),
path(
        'users/<int:user_id>/telegram-settings/',
        user_views.CoreSettingsViewSet.as_view(
            {'put': 'update', 'get': 'list', 'patch': 'partial_update'}
        )
    )
]