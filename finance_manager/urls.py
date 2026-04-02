"""
Root URL configuration for the finance_manager project.
Includes the tracker app URLs and the Django admin site.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tracker.urls')),
]
