from django.test.runner import DiscoverRunner
from django.conf import settings
from djcelery.app import app


def _set_eager():
    settings.CELERY_ALWAYS_EAGER = True
    app.conf.CELERY_ALWAYS_EAGER = True
    settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True  # Issue #75
    app.conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


class CeleryDiscoverTestSuiteRunner(DiscoverRunner):

    """Django test runner allowing testing of celery delayed tasks.

    All tasks are run locally, instead of on a worker.

    To use this runner set ``settings.TEST_RUNNER``::

        TEST_RUNNER = "atmosphere.test_runner.CeleryDiscoverTestSuiteRunner"

    """

    def setup_test_environment(self, **kwargs):
        _set_eager()
        super(
            CeleryDiscoverTestSuiteRunner,
            self).setup_test_environment(
            **kwargs)
