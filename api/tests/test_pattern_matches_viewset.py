from django.urls import reverse, resolve


class PatternMatchesViewsetTest(object):
    """
    A mixin which should be added to a TestCase, tests that a url pattern maps
    to a viewset.
    """

    def test_pattern_matches_viewset(self, url_pattern, view_set):
        """
        Assert that the url maps to the given viewset
        """
        url = reverse(url_pattern)
        match = resolve(url)
        view = match.func
        self.assertEqual(view.cls, view_set)
