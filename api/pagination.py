"""
custom pagination support
"""
from rest_framework.pagination import PageNumberPagination

# NOTE: this value is set here for v1 api support
DEFAULT_PAGINATION_SIZE = 20


def _is_positive(integer_string):
    """
    Check if a string is a strictly positive integer.
    """
    return int(integer_string) > 0


def _get_count(queryset):
    """
    Determine an object count, supporting either querysets or regular lists.
    """
    try:
        return queryset.count()
    except (AttributeError, TypeError):
        return len(queryset)

class StandardResultsSetPagination(PageNumberPagination):
    max_page_size = 1000
    page_size = 100
    page_size_query_param = 'page_size'

class OptionalPagination(PageNumberPagination):

    """
    Defaults to no pagination but supports pagination
    """
    page_size_query_param = 'page_size'
    max_page_size = None

    def paginate_queryset(self, queryset, request, view=None):
        if self.has_page(request):
            self.page_size = DEFAULT_PAGINATION_SIZE
        else:
            self.page_size = _get_count(queryset)

        return super(OptionalPagination, self).paginate_queryset(
            queryset, request, view=view)

    def has_page(self, request):
        """
        Checks whether a page has been specified
        """
        try:
            return _is_positive(request.query_params[self.page_query_param])
        except (KeyError, ValueError):
            return False
