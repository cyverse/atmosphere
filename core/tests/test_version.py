from django.test import TestCase
from atmosphere.version import get_version
import datetime
from dateutil.tz import tzoffset
import mock

class VersionTests(TestCase):
    def test_existing_version_behavior(self):
        git_head_info="f5d0849f7a6dbb608d2e5c81c16ac499b0af3a5f2018-03-07 10:00:35 -0700"
        git_branch_name="foobar"

        with mock.patch('atmosphere.version.VERSION', (9, 9, 9, 'dev', 9)):
            actual = get_version("all", git_branch_name=git_branch_name, git_head_info=git_head_info)

        expected = {
            'git_sha': 'f5d0849f7a6dbb608d2e5c81c16ac499b0af3a5',
            'git_sha_abbrev': '@f5d084',
            'short': '9.9.9',
            'verbose': '9.9.9 dev 9 @f5d084',
            'normal': '9.9.9 dev 9',
            'commit_date': datetime.datetime(2018, 3, 7, 10, 0, 35, tzinfo=tzoffset(None, -25200)),
            'git_branch': 'foobar',
            'branch': '9.9',
            'tertiary': '.9'
        }

        self.assertEqual(expected, actual);
