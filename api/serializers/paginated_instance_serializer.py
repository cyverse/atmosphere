from rest_framework import pagination
from .instance_serializer import InstanceSerializer


class PaginatedInstanceSerializer(pagination.PaginationSerializer):
    """
    Serializes page objects of Instance querysets.
    """
    class Meta:
        object_serializer_class = InstanceSerializer