from django.urls import path

from . import views

app_name = 'transactions'

urlpatterns = [
    path('summary/', views.SummaryView.as_view(), name='summary'),
    path('webapp/', views.my_view, name='webapp'),
    path('', views.HomePageView.as_view(), name='home'),
]
