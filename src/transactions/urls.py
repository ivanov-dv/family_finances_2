from django.urls import path

from . import views

app_name = 'transactions'

urlpatterns = [
    path('summary/', views.SummaryView.as_view(), name='summary'),
    path('', views.HomePageView.as_view(), name='home'),
    path('transactions/', views.TransactionView.as_view(), name='transactions')
]
