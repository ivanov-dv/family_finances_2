from django.urls import path

from . import views

app_name = 'export'

urlpatterns = [
    path('excel/', views.export_excel, name='excel'),
]
