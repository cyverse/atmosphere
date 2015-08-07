import factory
from core.models import Tag


class TagFactory(factory.DjangoModelFactory):

    class Meta:
        model = Tag

    name = 'tag-name'
    description = 'Tag description'
