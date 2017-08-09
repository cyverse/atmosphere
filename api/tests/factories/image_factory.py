import factory
from core.models import Application as Image
from .user_factory import UserFactory


class ImageFactory(factory.DjangoModelFactory):
    created_by = factory.SubFactory(UserFactory)

    class Meta:
        model = Image
