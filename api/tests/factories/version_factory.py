import factory
from core.models import ApplicationVersion
from .image_factory import ImageFactory
from .user_factory import UserFactory
from .identity_factory import IdentityFactory


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
    created_by = factory.SubFactory(UserFactory)     #factory.SelfAttribute("created_by_identity.created_by")
    created_by_identity = factory.LazyAttribute(
        lambda model: IdentityFactory(created_by=model.created_by))
