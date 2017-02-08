import factory
from core.models import ApplicationVersion
from .image_factory import ImageFactory


class ApplicationVersionFactory(factory.DjangoModelFactory):

    class Meta:
        model = ApplicationVersion

    application = factory.SubFactory(ImageFactory)
