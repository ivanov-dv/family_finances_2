from django.urls import path

from . import views

app_name = 'transactions'

urlpatterns = [
    path('apply_period/', views.apply_period, name='apply_period'),
    path('change_period', views.ChangePeriod.as_view(), name='change_period'),
    path('summary/', views.SummaryView.as_view(), name='summary'),
    path('transactions/', views.TransactionView.as_view(), name='transactions'),
    path('add-transaction/', views.AddTransactionView.as_view(), name='add_transaction'),
    path('groups/', views.AddSummaryView.as_view(), name='add_summary'),
    path('delete-summary/<int:pk>/', views.delete_summary, name='delete_summary'),
    path('', views.HomePageView.as_view(), name='home'),
]
