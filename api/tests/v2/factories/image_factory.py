import factory
from core.models import Application as Image
from django.contrib.auth.models import AnonymousUser


class ImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = Image
