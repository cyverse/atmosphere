import factory
from core.models import Leadership


class LeadershipFactory(factory.DjangoModelFactory):

    class Meta:
        model = Leadership
