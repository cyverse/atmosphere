import factory
from core.models import ProviderType


class ProviderTypeFactory(factory.DjangoModelFactory):

    class Meta:
        django_get_or_create = ("name",)
        model = ProviderType

    name = "mock"
