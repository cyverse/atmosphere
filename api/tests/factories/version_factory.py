import factory
from core.models import ApplicationVersion
from .image_factory import ImageFactory


class ApplicationVersionFactory(factory.DjangoModelFactory):

    @staticmethod
    def create_version(user, identity, application=None):
        if not application:
            application = ImageFactory.create(
                created_by_identity=identity,
                created_by=user)
        version = ApplicationVersionFactory.create(
            application=application,
            created_by_identity=identity,
            created_by=user)
        return version

    class Meta:
        model = ApplicationVersion

    application = factory.SubFactory(ImageFactory)
