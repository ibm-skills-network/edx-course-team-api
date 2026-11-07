"""
URLs for edx_course_team_api.
"""
from django.conf import settings
from django.urls import re_path

from .views import CourseView

urlpatterns = [
    re_path(fr'^{settings.COURSE_KEY_PATTERN}/modify_access', CourseView.as_view(), name='course'),
]
