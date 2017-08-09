import factory
from core.models import ApplicationVersion
from .image_factory import ImageFactory
from .user_factory import UserFactory


class ApplicationVersionFactory(factory.DjangoModelFactory):
    created_by = factory.SubFactory(UserFactory)

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
