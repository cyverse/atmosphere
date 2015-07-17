import factory
from core.models import Quota


class QuotaFactory(factory.DjangoModelFactory):

    class Meta:
        model = Quota
