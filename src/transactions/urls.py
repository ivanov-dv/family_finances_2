from django.urls import path

from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home'),
    path('summary/', views.SummaryView.as_view(), name='summary'),
]
