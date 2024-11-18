from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.v1.users import views

app_name = 'api_v1'

router_v1 = DefaultRouter()
router_v1.register('users', views.UserViewSet, basename='users')

urlpatterns = [
    path('', include(router_v1.urls))
]