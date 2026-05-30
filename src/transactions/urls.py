from django.urls import path

from . import views

app_name = 'transactions'

urlpatterns = [
    path('spaces/apply/', views.ApplySpaceView.as_view(), name='apply_space'),
    path('spaces/<int:pk>/leave/', views.LeaveSpaceView.as_view(), name='leave_space'),
    path('spaces/create/', views.CreateSpaceView.as_view(), name='create_space'),
    path('spaces/<int:pk>/rename/', views.RenameSpaceView.as_view(), name='rename_space'),
    path('spaces/<int:pk>/delete/', views.DeleteSpaceView.as_view(), name='delete_space'),
    path('spaces/<int:pk>/invite/', views.InviteUserView.as_view(), name='invite_user'),
    path('spaces/<int:pk>/role/', views.ChangeMemberRoleView.as_view(), name='change_member_role'),
    path('spaces/<int:pk>/remove-member/', views.RemoveMemberView.as_view(), name='remove_member'),
    path('apply_period/', views.apply_period, name='apply_period'),
    path('create_period/', views.create_period, name='create_period'),
    path('change_period', views.ChangePeriod.as_view(), name='change_period'),
    path('summary/', views.SummaryView.as_view(), name='summary'),
    path('transactions/', views.TransactionView.as_view(), name='transactions'),
    path('add-transaction/', views.AddTransactionView.as_view(), name='add_transaction'),
    path('groups/', views.AddSummaryView.as_view(), name='add_summary'),
    path('delete-summary/<int:pk>/', views.delete_summary, name='delete_summary'),
    path('', views.HomePageView.as_view(), name='home'),
]
