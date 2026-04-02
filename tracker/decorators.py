"""
Custom decorators for role-based access control.

Enforces permissions actively on the endpoints:
  - Admin: Full access
  - Analyst: Can view + filter + see analytics
  - Viewer: Can only view records
"""

from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden


def get_user_role(user):
    """
    Determine the user's role based on their profile.
    Superusers automatically receive Admin privileges.
    """
    if user.is_superuser:
        return 'Admin'

    if hasattr(user, 'profile'):
        return user.profile.role

    # Default fallback conceptually
    return 'Viewer'


def role_required(allowed_roles):
    """
    Decorator that restricts view access to users with specific roles.
    Usage: @role_required(['Admin', 'Analyst'])
    Returns 403 if unauthorized.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            user_role = get_user_role(request.user)
            if user_role not in allowed_roles:
                return HttpResponseForbidden("<h1>403 Forbidden</h1><p>You do not have permission to access this page.</p>")

            # Attach role to request for use in templates
            request.user_role = user_role
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
