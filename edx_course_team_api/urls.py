"""
URLs for edx_course_team_api.
"""
from django.conf import settings
from django.urls import re_path

from .views import CourseView

urlpatterns = [
    re_path(fr'^{settings.COURSE_KEY_PATTERN}/modify_access', CourseView.as_view(), name='course'),
]

# # Since urls.py is executed once, create service user here for server to server auth
# from django.contrib.auth.models import User
# try:
#     User.objects.get(username=settings.AUTH_USERNAME)
# except User.DoesNotExist:
#     User.objects.create_user(username=settings.AUTH_USERNAME,
#                                     email=settings.EMAIL,
#                                     password=settings.AUTH_PASSWORD, is_staff=True)
