"""
URL routing for the tracker app.
Maps URL paths to view functions.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Transaction CRUD
    path('transactions/', views.transaction_list_view, name='transaction_list'),
    path('transactions/add/', views.transaction_create_view, name='transaction_create'),
    path('transactions/<int:pk>/edit/', views.transaction_update_view, name='transaction_update'),
    path('transactions/<int:pk>/delete/', views.transaction_delete_view, name='transaction_delete'),

    # CSV Export
    path('transactions/export/', views.export_csv_view, name='export_csv'),

    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(
        template_name='tracker/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('create-user/', views.create_user_temp),
]
