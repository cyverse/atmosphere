"""
https://gist.github.com/2204099.git
Author contact: sepero 111 @ gmail . com
"""

from django import http
from django.utils.http import urlquote
from django.core import urlresolvers

from threepio import logger

class RemoveCSRFMiddleware(object):

    """
    This middleware disables CSRF from the DRF endpoints (Namespaced by /api/...)
    """

    def process_request(self, request):
        # check if the url is valid
        path = new_path = request.path_info
        if '/api' in new_path:
            setattr(request, '_dont_enforce_csrf_checks', True)


class RemoveSlashMiddleware(object):

    """
    This middleware works like django's built in APPEND_SLASH, but in reverse. Eg
    It removes all ending slashes from a URL, and if that doesn't resolve, it will add one slash and try again.
    Set APPEND_SLASH to False when using this middleware.

    Forked from the original code at http://gregbrown.co.nz/code/append-or-remove-slash/
    """

    def process_request(self, request):
        # check if the url is valid
        path = new_path = request.path_info
        # Remove all trailing slashes from new_path.
        while new_path.endswith('/'):
            new_path = new_path[:-1]
        urlconf = getattr(request, 'urlconf', None)
        if not _is_valid_path(new_path, urlconf):
            # If removing slashes made new_path invalid, add one slash and try
            # again.
            new_path = new_path + '/'
            if path != new_path and _is_valid_path(new_path, urlconf):
                return self.adjust_path(request, new_path)
        elif path != new_path:
            # If new_path is valid and not eq to path, send a permanent
            # redirect.
            return self.adjust_path(request, new_path)

    def adjust_path(self, request, new_path):
        """
        Redirect the clients browser to new_path, and tell it that all future requests to the desired URL should be sent to new_path. (This method looks like it may be able to be made more efficient, but I'm not familiar enough with request.path_info and other django variables to know how.)
        """
        if request.get_host():
            new_url = "%s://%s%s" % ('https',
                                     request.get_host(),
                                     urlquote(new_path))
        else:
            new_url = urlquote(new_path)
        if request.GET:
            new_url += '?' + request.META['QUERY_STRING']
        return http.HttpResponseRedirect(new_url)


def _is_valid_path(path, urlconf=None):
    """
    Returns True if the given path resolves against the default URL resolver,
    False otherwise.
    """
    try:
        urlresolvers.resolve(path, urlconf)
        return True
    except urlresolvers.Resolver404:
        return False

""" Author contact: sepero 111 @ gmail . com """
