"""
Tests for the modify_access endpoint, which grants and revokes course team roles.

The requests go through real HTTP Basic auth and the IsServiceAccount permission.
``auth`` and ``CourseEnrollment`` are patched, so these tests pin what this plugin
checks and passes, not edx-platform's own checks. edx-platform's add_users also
refuses a caller who has no authority over the role.
"""

import base64
import json
import secrets
from unittest import mock
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole
from edx_course_team_api import views

# Must match AUTH_USERNAME in test_settings.py.
SERVICE_USERNAME = 'sn-service'
SERVICE_EMAIL = 'service@place.com'
SERVICE_PASSWORD = secrets.token_hex(8)
SERVICE_CREDENTIALS = (SERVICE_USERNAME, SERVICE_PASSWORD)

# A superuser that is NOT the service account -- must still be rejected.
ADMIN_USERNAME = 'other-admin'
ADMIN_EMAIL = 'other-admin@place.com'
ADMIN_PASSWORD = secrets.token_hex(8)

LEARNER_USERNAME = 'learner'
LEARNER_EMAIL = 'learner@place.com'
LEARNER_PASSWORD = secrets.token_hex(8)

TARGET_USERNAME = 'target'
TARGET_EMAIL = 'target@place.com'
TARGET_PASSWORD = secrets.token_hex(8)

COURSE_KEY_STRING = 'course-v1:edX+DemoX+Demo_Course'


def basic_auth(username, password):
    """Build an HTTP Basic Auth header value for the given credentials."""
    token = base64.b64encode(
        '{username}:{password}'.format(username=username, password=password).encode()
    ).decode()
    return 'Basic {token}'.format(token=token)


class CourseTeamTestMixin(object):
    """
    Shared authorization/validation tests for both the grant and revoke methods.

    Subclasses must set ``method`` to the HTTP verb they exercise.
    """

    method = None

    def setUp(self):
        self.client = Client()
        self.service_account = User.objects.create_user(
            SERVICE_USERNAME, SERVICE_EMAIL, SERVICE_PASSWORD, is_staff=True
        )
        self.other_admin = User.objects.create_superuser(
            ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD
        )
        self.learner = User.objects.create_user(
            LEARNER_USERNAME, LEARNER_EMAIL, LEARNER_PASSWORD
        )
        self.target = User.objects.create_user(
            TARGET_USERNAME, TARGET_EMAIL, TARGET_PASSWORD
        )
        self.url = reverse('course', kwargs={'course_key_string': COURSE_KEY_STRING})
        self.body = {'email': TARGET_EMAIL, 'role': 'staff'}
        self.auth = self.patch_view('auth')
        self.enrollment = self.patch_view('CourseEnrollment')

    def patch_view(self, attribute):
        """Patch a module-level name in views for the duration of one test."""
        patcher = mock.patch.object(views, attribute)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def request(self, credentials=None, body=None, form_encoded=False):
        """Issue the request under test, optionally authenticated via Basic Auth."""
        kwargs = {}
        if credentials is not None:
            kwargs['HTTP_AUTHORIZATION'] = basic_auth(*credentials)
        payload = self.body if body is None else body
        if form_encoded:
            kwargs['content_type'] = 'application/x-www-form-urlencoded'
            data = urlencode(payload)
        else:
            kwargs['content_type'] = 'application/json'
            data = json.dumps(payload)
        return getattr(self.client, self.method)(self.url, data, **kwargs)

    def assert_no_access_change(self):
        """Assert the request granted, revoked and enrolled nothing."""
        self.assertFalse(self.auth.add_users.called)
        self.assertFalse(self.auth.remove_users.called)
        self.assertFalse(self.enrollment.enroll.called)
        self.assertFalse(self.enrollment.unenroll.called)

    def test_requires_authentication(self):
        res = self.request()
        self.assertEqual(res.status_code, 401)
        self.assert_no_access_change()

    def test_forbidden_for_learner(self):
        """An authenticated non-staff learner never reaches the view."""
        res = self.request(credentials=(LEARNER_USERNAME, LEARNER_PASSWORD))
        self.assertEqual(res.status_code, 403)
        self.assert_no_access_change()

    def test_forbidden_for_non_service_superuser(self):
        """Even a real superuser is rejected unless it is the service account."""
        res = self.request(credentials=(ADMIN_USERNAME, ADMIN_PASSWORD))
        self.assertEqual(res.status_code, 403)
        self.assert_no_access_change()

    @override_settings(AUTH_USERNAME=LEARNER_USERNAME)
    def test_forbidden_when_username_matches_but_not_staff(self):
        """Anyone can register on a portal, so a learner could take the service account's username."""
        res = self.request(credentials=(LEARNER_USERNAME, LEARNER_PASSWORD))
        self.assertEqual(res.status_code, 403)
        self.assert_no_access_change()

    @override_settings(AUTH_USERNAME='')
    def test_fails_closed_when_service_account_unset(self):
        """Studio does not start without AUTH_USERNAME. This asserts an empty one still lets nobody in."""
        res = self.request(credentials=SERVICE_CREDENTIALS)
        self.assertEqual(res.status_code, 403)
        self.assert_no_access_change()

    def test_400_missing_email(self):
        res = self.request(credentials=SERVICE_CREDENTIALS, body={'role': 'staff'})
        self.assertEqual(res.status_code, 400)
        self.assert_no_access_change()

    def test_404_missing_user(self):
        res = self.request(
            credentials=SERVICE_CREDENTIALS,
            body={'email': 'nobody@place.com', 'role': 'staff'},
        )
        self.assertEqual(res.status_code, 404)
        self.assert_no_access_change()


class TestGrantCourseTeamRole(CourseTeamTestMixin, TestCase):
    """Tests for POST /<course_key>/modify_access."""

    method = 'post'

    def test_grant_success_as_service_account(self):
        res = self.request(credentials=SERVICE_CREDENTIALS)
        self.assertEqual(res.status_code, 200)
        self.auth.add_users.assert_called_once()
        caller, role, granted = self.auth.add_users.call_args[0]
        self.assertEqual(caller, self.service_account)
        self.assertEqual(granted, self.target)
        self.assertIsInstance(role, CourseStaffRole)

    def test_grant_enrolls_by_default(self):
        """Upstream auto-enrolls so that "View Live" works; keep that the default."""
        self.request(credentials=SERVICE_CREDENTIALS)
        self.enrollment.enroll.assert_called_once()
        enrolled, course_key = self.enrollment.enroll.call_args[0]
        self.assertEqual(enrolled, self.target)
        self.assertEqual(str(course_key), COURSE_KEY_STRING)

    def test_grant_instructor(self):
        self.request(credentials=SERVICE_CREDENTIALS, body={'email': TARGET_EMAIL, 'role': 'instructor'})
        _, role, _ = self.auth.add_users.call_args[0]
        self.assertIsInstance(role, CourseInstructorRole)
        self.assertEqual(str(role.course_key), COURSE_KEY_STRING)

    def test_400_unknown_role(self):
        res = self.request(
            credentials=SERVICE_CREDENTIALS,
            body={'email': TARGET_EMAIL, 'role': 'superhero'},
        )
        self.assertEqual(res.status_code, 400)
        self.assert_no_access_change()

    def test_405_unsupported_methods(self):
        header = basic_auth(*SERVICE_CREDENTIALS)
        self.assertEqual(self.client.get(self.url, HTTP_AUTHORIZATION=header).status_code, 405)
        for method in (self.client.put, self.client.patch):
            res = method(
                self.url, json.dumps(self.body),
                content_type='application/json', HTTP_AUTHORIZATION=header,
            )
            self.assertEqual(res.status_code, 405)


class TestRevokeCourseTeamRole(CourseTeamTestMixin, TestCase):
    """Tests for DELETE /<course_key>/modify_access."""

    method = 'delete'

    def test_revoke_success_as_service_account(self):
        res = self.request(credentials=SERVICE_CREDENTIALS)
        self.assertEqual(res.status_code, 200)
        revoked_from = [call[0][2] for call in self.auth.remove_users.call_args_list]
        self.assertEqual(revoked_from, [self.target, self.target])
        roles = [type(call[0][1]) for call in self.auth.remove_users.call_args_list]
        self.assertEqual(roles, [CourseStaffRole, CourseInstructorRole])
        unenrolled, course_key = self.enrollment.unenroll.call_args[0]
        self.assertEqual(unenrolled, self.target)
        self.assertEqual(str(course_key), COURSE_KEY_STRING)
