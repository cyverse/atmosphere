from rest_framework import pagination
from .get_context_user import get_context_user
from .application_serializer import ApplicationSerializer


class PaginatedApplicationSerializer(pagination.PaginationSerializer):
    """
    Serializes page objects of Instance querysets.
    """

    def __init__(self, *args, **kwargs):
        user = get_context_user(self, kwargs)
        self.request_user = user
        super(PaginatedApplicationSerializer, self).__init__(*args, **kwargs)

    class Meta:
        object_serializer_class = ApplicationSerializer