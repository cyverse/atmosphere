import factory
from core.models import ApplicationBookmark as ImageBookmark


class ImageBookmarkFactory(factory.DjangoModelFactory):

    class Meta:
        model = ImageBookmark
