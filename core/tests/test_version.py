from django.test import TestCase
from django.conf import settings
from atmosphere.version import git_version_lookup
import datetime
from dateutil.tz import tzoffset

class VersionTests(TestCase):
    def test_existing_version_behavior(self):
        git_head_info="f5d0849f7a6dbb608d2e5c81c16ac499b0af3a5f2018-03-07 10:00:35 -0700"
        git_branch_name="foobar"

        actual = git_version_lookup(git_branch_name=git_branch_name, git_head_info=git_head_info)

        expected = {
            'git_sha': 'f5d0849f7a6dbb608d2e5c81c16ac499b0af3a5',
            'git_sha_abbrev': '@f5d084',
            'commit_date': datetime.datetime(2018, 3, 7, 10, 0, 35, tzinfo=tzoffset(None, -25200)),
            'git_branch': 'foobar',
        }

        self.assertEqual(expected, actual);
