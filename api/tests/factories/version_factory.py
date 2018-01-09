import factory
from core.models import ApplicationVersion
from .image_factory import ImageFactory


class ApplicationVersionFactory(factory.DjangoModelFactory):

    @staticmethod
    def create_version(user, identity, application=None, end_date=None):
        if not application:
            application = ImageFactory.create(
                created_by_identity=identity,
                created_by=user)
        version = ApplicationVersionFactory.create(
            application=application,
            created_by_identity=identity,
            created_by=user,
            end_date=end_date)
        return version

    class Meta:
        model = ApplicationVersion

    application = factory.SubFactory(ImageFactory)
