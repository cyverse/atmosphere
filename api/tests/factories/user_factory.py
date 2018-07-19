import factory
from core.models import AtmosphereUser as User
from django.contrib.auth.models import AnonymousUser


class UserFactory(factory.DjangoModelFactory):

    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: 'user%d' % n)


class AnonymousUserFactory(factory.Factory):

    class Meta:
        model = AnonymousUser
