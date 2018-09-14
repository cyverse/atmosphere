import factory
from core.models import Application as Image
from .user_factory import UserFactory


class ImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = Image

    created_by = factory.SubFactory(UserFactory)
