from django.urls import path

from users import views

app_name = 'users'

urlpatterns = [
    path('ajax-login/', views.login_ajax, name='ajax_login'),
    path('telegram-auth/', views.telegram_auth, name='telegram_auth'),
    path('registration/', views.registration, name='registration'),
]
