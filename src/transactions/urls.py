from django.urls import path

from . import views

app_name = 'transactions'

urlpatterns = [
    path('apply_period/', views.apply_period, name='apply_period'),
    path('change_period', views.ChangePeriod.as_view(), name='change_period'),
    path('summary/', views.SummaryView.as_view(), name='summary'),
    path('transactions/', views.TransactionView.as_view(), name='transactions'),
    path('', views.HomePageView.as_view(), name='home'),
]
