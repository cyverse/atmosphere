import factory
from core.models import Tag


class TagFactory(factory.DjangoModelFactory):

    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: 'tag-name-%d' % n)
    description = 'Tag description'
