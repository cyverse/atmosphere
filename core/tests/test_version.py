import os
from django.test import TestCase
from django.conf import settings
from atmosphere.version import git_version_lookup
import datetime
from dateutil.tz import tzoffset


class VersionTests(TestCase):
    def test_version_format(self):
        """
        Test expected behavior when git_version_lookup is just formatting output from git
        """
        actual = git_version_lookup(
            git_branch_name="foobar",
            git_head_info=
            "f5d0849f7a6dbb608d2e5c81c16ac499b0af3a5f2018-03-07 10:00:35 -0700"
        )

        expected = {
            'git_sha':
                'f5d0849f7a6dbb608d2e5c81c16ac499b0af3a5',
            'git_sha_abbrev':
                '@f5d084',
            'commit_date':
                datetime.datetime(
                    2018, 3, 7, 10, 0, 35, tzinfo=tzoffset(None, -25200)
                ),
            'git_branch':
                'foobar',
        }

        self.assertEqual(expected, actual)

    def test_version_lookup(self):
        """
        Test expected behavior when git_version_lookup retrieves output from git
        """
        git_directory = os.path.join(settings.PROJECT_ROOT, ".git")
        version = git_version_lookup(git_directory=git_directory)

        keys = ['git_sha', 'git_sha_abbrev', 'commit_date', 'git_branch']
        for key in keys:
            self.assertIn(key, version)
            self.assertIsNotNone(version[key])
