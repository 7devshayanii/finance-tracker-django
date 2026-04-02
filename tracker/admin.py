"""
Admin configuration for the Finance Tracking System.

Registers the Transaction model with the Django admin site
for quick management and debugging.
"""

from django.contrib import admin
from .models import Transaction, Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username',)



@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'category', 'amount', 'date', 'created_at')
    list_filter = ('type', 'category', 'date')
    search_fields = ('description', 'user__username')
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')
