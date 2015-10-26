from rest_framework import serializers

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
