"""
Template context processor that makes the user's role available in all templates.
"""

from .decorators import get_user_role


def user_role_processor(request):
    """Add the user's role to the template context."""
    if request.user.is_authenticated:
        return {'user_role': get_user_role(request.user)}
    return {'user_role': None}
