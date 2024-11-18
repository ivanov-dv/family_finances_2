from django.contrib import admin
from django.urls import path, include, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

urlpatterns = [
    path('api/v1/', include('api.v1.urls', namespace='api_v1')),
    path('admin/', admin.site.urls),
]


# Генерация динамической документации
schema_view = get_schema_view(
    info=openapi.Info(
      title="Reference API",
      default_version='v1',
      description="RESTful API справочника"
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)
urlpatterns += [
   re_path(r'^swagger(?P<format>\.json|\.yaml)$',
       schema_view.without_ui(cache_timeout=0), name='schema-json'),
   path('swagger/', schema_view.with_ui('swagger', cache_timeout=0),
       name='schema-swagger-ui'),
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0),
       name='schema-redoc'),
]
