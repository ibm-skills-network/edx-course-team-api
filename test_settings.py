"""
These settings are here to use during tests, because django requires them.
In a real-world use case, apps in this project are installed into other
Django applications, so these settings will not be used.
"""

from os.path import abspath, dirname, join


def root(*args):
    """
    Get the absolute path of the given path relative to the project root.
    """
    return join(abspath(dirname(__file__)), *args)


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'default.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    'edx_course_team_api',
)

LOCALE_PATHS = [
    root('edx_course_team_api', 'conf', 'locale'),
]

ROOT_URLCONF = 'edx_course_team_api.urls'

SECRET_KEY = 'insecure-secret-key'

# Every test authenticates over HTTP Basic, which rehashes the password on each
# request; the default PBKDF2 hasher turns the suite into a two-minute run.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Username of the dedicated service account allowed to call the course-team
# grant/revoke endpoint (see the IsServiceAccount permission). In Studio this
# is set by settings.common.plugin_settings from the environment.
AUTH_USERNAME = 'sn-service'

# Studio supplies this from openedx.core.constants; urls.py builds the endpoint
# pattern out of it.
COURSE_KEY_PATTERN = r'(?P<course_key_string>[^/+]+(/|\+)[^/+]+(/|\+)[^/?]+)'
