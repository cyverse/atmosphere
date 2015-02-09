import factory
from core.models import VolumeAction


class VolumeActionFactory(factory.DjangoModelFactory):
    class Meta:
        model = VolumeAction
