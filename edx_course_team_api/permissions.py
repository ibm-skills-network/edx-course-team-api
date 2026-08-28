"""
Custom DRF permissions for edx_course_team_api.
"""
from django.conf import settings
from rest_framework.permissions import BasePermission


class IsServiceAccount(BasePermission):
    """
    Allow access only to the dedicated course-team-api service account.

    The caller must be an authenticated staff user whose username matches the
    configured ``AUTH_USERNAME`` setting. This restricts the privilege-granting
    endpoints to a single known integration account rather than to any
    authenticated (or even any staff/superuser) user.

    Fails closed: if ``AUTH_USERNAME`` is unset or empty, no caller is allowed.
    """

    def has_permission(self, request, view):
        """Return True only for the configured, authenticated service account."""
        service_username = getattr(settings, 'AUTH_USERNAME', None)
        if not service_username:
            return False
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and user.username == service_username
        )
