import factory
from core.models import Application as Image


class ImageFactory(factory.DjangoModelFactory):

    class Meta:
        model = Image
