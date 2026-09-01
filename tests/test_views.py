#!/usr/bin/env python
"""
Tests for the `edx_course_team_api` views module.

These exercise the real authentication (HTTP Basic Auth) and authorization
(service-account only) behaviour of the modify_access endpoint, including a
regression test proving that neither an ordinary learner nor an unrelated
superuser can hand themselves a course-team role. Only the configured
``AUTH_USERNAME`` service account may call this endpoint.
"""

import base64
import json
from unittest import mock
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from common.djangoapps.student.roles import CourseStaffRole
from edx_course_team_api import views

# Must match AUTH_USERNAME in test_settings.py.
SERVICE_USERNAME = 'sn-service'
SERVICE_EMAIL = 'service@place.com'
SERVICE_PASSWORD = 'servicepass123'
SERVICE_CREDENTIALS = (SERVICE_USERNAME, SERVICE_PASSWORD)

# A superuser that is NOT the service account -- must still be rejected.
ADMIN_USERNAME = 'other-admin'
ADMIN_EMAIL = 'other-admin@place.com'
ADMIN_PASSWORD = 'adminpass123'

LEARNER_USERNAME = 'learner'
LEARNER_EMAIL = 'learner@place.com'
LEARNER_PASSWORD = 'learnerpass123'

TARGET_USERNAME = 'target'
TARGET_EMAIL = 'target@place.com'
TARGET_PASSWORD = 'targetpass123'

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
        # The edx-platform side effects live behind mock_apps, so patching them
        # here is the only way to observe what the view actually did.
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
        """Core regression: an authenticated non-staff learner is rejected."""
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
        """The is_staff clause blocks a username match on a non-staff account.

        Guards against username squatting: with open registration an attacker
        could self-register the configured service-account username, so matching
        the name must not be sufficient without staff status.
        """
        res = self.request(credentials=(LEARNER_USERNAME, LEARNER_PASSWORD))
        self.assertEqual(res.status_code, 403)
        self.assert_no_access_change()

    @override_settings(AUTH_USERNAME='')
    def test_fails_closed_when_service_account_unset(self):
        """Defence in depth: no AUTH_USERNAME, no caller -- not even the service account.

        settings.common refuses to boot Studio without AUTH_USERNAME, so this
        state is unreachable in production; the branch exists so a future
        settings change cannot quietly open the endpoint up.
        """
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

    def test_revoke_leaves_enrollment_alone(self):
        """Revoking a role must not unenroll: upstream's course-team handler never does.

        Unenrolling here costs a genuinely enrolled learner their course access,
        progress and certificate eligibility -- from a call that only asked to
        take a role away. Callers wanting an unenroll have the instructor
        enrollment API for that.
        """
        res = self.request(credentials=SERVICE_CREDENTIALS)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(self.auth.remove_users.called)
        self.assertFalse(self.enrollment.unenroll.called)
