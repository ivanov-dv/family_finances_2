from django.urls import path

from transactions import views

app_name = 'transactions'

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home'),
    path('summary/', views.SummaryView.as_view(), name='summary'),
    path('ajax-login/', views.login_ajax, name='ajax_login'),
    path('registration/', views.registration, name='registration'),
]