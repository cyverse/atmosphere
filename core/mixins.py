"""
core.mixins - Mixins available to use with models
"""
from django.db.models.signals import post_save


def on_changed(sender, **kwargs):
    """
    Calls the `model_changed` method and then resets the state.
    """
    instance = kwargs.get("instance")
    is_new = kwargs.get("created")
    dirty_fields = instance.get_dirty_fields()
    instance.model_changed(instance.original_state, dirty_fields, is_new)
    instance.original_state = instance.to_dict()


class ModelChangedMixin(object):
    """
    Mixin for detecting changes to a model
    """
    def __init__(self, *args, **kwargs):
        super(ModelChangedMixin, self).__init__(*args, **kwargs)
        self.original_state = self.to_dict()
        identifier = "{0}_model_changed".format(self.__class__.__name__)
        post_save.connect(
            on_changed, sender=self.__class__, dispatch_uid=identifier)

    def to_dict(self):
        """
        Returns the model as a dict
        """
        # Get all the field names that are not relations
        keys = (f.name for f in self._meta.local_fields if not f.rel)
        return {field: getattr(self, field) for field in keys}

    def get_dirty_fields(self):
        """
        Returns the fields dirty on the model
        """
        dirty_fields = {}
        current_state = self.to_dict()

        for key, value in current_state.items():
            if self.original_state[key] != value:
                dirty_fields[key] = value

        return dirty_fields

    def is_dirty(self):
        """
        Return whether the model is dirty

        An unsaved model is dirty when it has no primary key
        or has at least one dirty field.
        """
        if not self.pk:
            return True

        return {} != self.get_dirty_fields()

    def model_changed(self, old_fields, new_fields, is_new):
        """
        Post-hook for all fields that have been changed.
        """
        raise NotImplementedError("Missing method `model_changed`")
