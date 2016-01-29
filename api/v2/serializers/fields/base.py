from django.core.exceptions import ObjectDoesNotExist
from django.db import ProgrammingError
from rest_framework import exceptions
from rest_framework import serializers

class ModelRelatedField(serializers.RelatedField):
    """
    Related field that renders the representation based on `serializer_class`
    and converts to an internal representation using `lookup_field`.
    """
    lookup_field = "pk"

    def __init__(self, *args, **kwargs):
        self.serializer_class = kwargs.pop("serializer_class")
        self.lookup_field = kwargs.pop("lookup_field", self.lookup_field)
        super(ModelRelatedField, self).__init__(*args, **kwargs)

    def get_queryset(self):
        assert self.queryset is not None, (
            "%s should have a `queryset` attribute."
            % self.___class__.__name__
        )
        return self.queryset.all()

    def to_representation(self, value):
        assert self.serializer_class is not None, (
            "%s should have a `serializer_class` attribute."
            % self.___class__.__name__
        )
        queryset = self.get_queryset()
        obj = queryset.get(pk=value.pk)
        serializer = self.serializer_class(obj, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, dict):
            identifier = data.get(self.lookup_field, None)
        else:
            identifier = data
        try:
            return queryset.get(**{self.lookup_field: identifier})
        except (TypeError, ValueError,
                ProgrammingError, ObjectDoesNotExist):
            raise exceptions.ValidationError(
                "%s with Field: %s '%s' does not exist."
                % (self.queryset.model.__name__, self.lookup_field, identifier)
            )

class ReprSlugRelatedField(serializers.SlugRelatedField):
    def __init__(self, slug_field=None, repr_slug_field=None, **kwargs):
        assert slug_field is not None, 'The `slug_field` argument is required.'
        assert repr_slug_field is not None, 'The `repr_slug_field` argument is required.'
        self.slug_field = slug_field
        self.repr_slug_field = repr_slug_field
        super(ReprSlugRelatedField, self).__init__(slug_field=slug_field, **kwargs)


    def to_representation(self, obj):
        return getattr(obj, self.repr_slug_field)

class DebugHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    def __init__(self, view_name=None, **kwargs):
        return super(DebugHyperlinkedIdentityField, self).__init__(view_name=view_name, **kwargs)


    def get_url(self, obj, view_name, request, format):
        """
        """
        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, 'pk') and obj.pk is None:
            return None

        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {self.lookup_url_kwarg: lookup_value}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

class UUIDHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    lookup_field ='uuid'
    lookup_url_kwarg = 'uuid'
    #
    uuid_field = None
    def __init__(self, view_name=None, uuid_field="uuid", **kwargs):
        assert view_name is not None, 'The `view_name` argument is required.'
        kwargs['read_only'] = True
        kwargs['source'] = '*'
        self.uuid_field = uuid_field
        super(UUIDHyperlinkedIdentityField, self).__init__(view_name, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object based on lookup_field. Raises a 'NoReverseMatch' without a 'lookup_field'.
        """
        if obj.pk is None:
            return None
        obj_uuid = getattr(obj, self.uuid_field)
        if obj_uuid is None:
            raise Exception("UUID Field '%s' is missing - Check Field constructor" % obj_uuid)

        return self.reverse(view_name,
            kwargs={
                'pk': obj_uuid,
            },
            request=request,
            format=format,
        )
class InstanceSourceHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    def __init__(self, view_name=None, **kwargs):
        super(InstanceSourceHyperlinkedIdentityField, self).__init__(view_name, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object based on lookup_field. Raises a 'NoReverseMatch' without a 'lookup_field'.
        """
        if obj.pk is None or not getattr(obj,"instance_source"):
            return None
        obj_uuid = obj.instance_source.identifier
        if obj_uuid is None:
            raise Exception("UUID Field '%s' is missing - Check Field constructor" % obj_uuid)

        return self.reverse(view_name,
            kwargs={
                'pk': obj_uuid,
            },
            request=request,
            format=format,
        )
