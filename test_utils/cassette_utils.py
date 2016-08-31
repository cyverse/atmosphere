from urlparse import urlparse


def assert_cassette_playback_length(cassette, expected_cassette_length):
    """Make sure the cassette is:
     1. The expected length and either
     2. New (dirty) or
     3. Existing, rewound
     """
    assert len(cassette) == expected_cassette_length
    assert (cassette.dirty or cassette.all_played)


def scrub_host_name(request):
    """Replaces any host name with 'localhost'"""
    parse_result = urlparse(request.uri)
    # noinspection PyProtectedMember
    scrubbed_parts = parse_result._replace(netloc='localhost')
    request.uri = scrubbed_parts.geturl()
    return request
