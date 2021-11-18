import logging
import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ParseError
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User

# edx imports
from common.djangoapps.student import auth
from common.djangoapps.student.models import CourseEnrollment
from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole
from opaque_keys.edx.keys import CourseKey
from cms.djangoapps.contentstore.views.user import _course_team_user


log = logging.getLogger(__name__)

USERNAME = 'admin'  # the user who will be associated with new courses

ROLE_TYPE_MAPPINGS = {
    "staff": CourseStaffRole,
    "instructor": CourseInstructorRole
}
ROLE_OPTIONS = list(ROLE_TYPE_MAPPINGS.keys())


class CourseView(APIView):

    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, course_key_string):
        course_key = CourseKey.from_string(course_key_string)

        email = request.data.get("email", None)
        if not email:
            msg = {"error": "Missing parameter 'email' in body."}
            log.info(msg)
            raise ParseError(msg)

        role = request.data.get("role", None)
        if not role:
            msg = {"error": "Missing parameter 'role' in body."}
            log.info(msg)
            raise ParseError(msg)

        if role not in ROLE_OPTIONS:
            msg = {"error": "Parameter 'role' has to be one of '{}'".format(ROLE_OPTIONS)}
            log.info(msg)
            raise ParseError(msg)

        try:
            user = User.objects.get(email=email)
        except Exception:  # pylint: disable=broad-except
            msg = {
                "error": "Could not find user by email address '{email}'".format(email=email)
            }
            return Response(msg, 404)

        role_type = ROLE_TYPE_MAPPINGS.get(role)(course_key)
        auth.add_users(request.user, role_type, user)
        CourseEnrollment.enroll(user, course_key)

        msg = "'{email}' is granted '{role}' to '{course_key}'".format(email=email, role=role, course_key=course_key)
        log.info(msg)

        return Response({'message': "User is added to {}.".format(course_key)})
