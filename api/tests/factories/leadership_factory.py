import factory
from core.models import Leadership


class LeadershipFactory(factory.DjangoModelFactory):

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        leadership = model_class(*args, **kwargs)
        leadership.save()
        # This happens by default in Atmosphere, but is not reflected in the LeadershipFactory alone.
        user = leadership.user
        group = leadership.group
        group.user_set.add(user)
        return leadership

    class Meta:
        model = Leadership
