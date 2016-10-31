import json_delta


def dict_eq_(test_case, dict1, dict2):
    diff = json_delta.udiff(dict1, dict2, entry=True)
    diff_lines = ''
    for line in diff:
        diff_lines = '{}{}\n'.format(diff_lines, line)
        test_case.assertEqual(dict2, dict1, diff_lines)
