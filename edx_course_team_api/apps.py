"""
edx_course_team_api Django application initialization.
"""

from django.apps import AppConfig


class EdxCourseTeamApiConfig(AppConfig):
    """
    Configuration for the edx_course_team_api Django application.
    """

    name = 'edx_course_team_api'
    plugin_app = {
        'url_config': {
            'cms.djangoapp': {
                'namespace': 'edx_course_team_api',
                'regex': r'^sn-api/course-team/',
            },
        },
        'settings_config': {
            'cms.djangoapp': {
                'common': {'relative_path': 'settings.common'},
            },
        },
    }
