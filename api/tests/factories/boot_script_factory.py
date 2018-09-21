import factory
from factory import fuzzy
from api.tests.factories import UserFactory
from core.models import BootScript, ScriptType


class BootScriptFactory(factory.DjangoModelFactory):
    class Meta:
        model = BootScript

    title = fuzzy.FuzzyText(prefix="bootscript-title-")
    created_by = factory.SubFactory(UserFactory)


class BootScriptRawTextFactory(BootScriptFactory):
    script_type = factory.LazyAttribute(
        lambda _: ScriptType.objects.get_or_create(name='Raw Text')[0]
    )
