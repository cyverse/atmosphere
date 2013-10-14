"""
Provide pluggable machine search for Atmosphere.

"""


from abc import ABCMeta, abstractmethod

from django.db.models import Q

from core.models.machine import compare_core_machines, filter_core_machine,\
    convert_esh_machine, update_machine_metadata,\
    ProviderMachine


def search(providers, identity, query):
    return reduce(|, [p.search(identity, qeuery) for p in providers])
        


class BaseSearchProvider():
    """
    BaseSearchProvider lists a basic set of expected functionality for
    search providers.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def search(identity, query):
        raise NotImplementedError


class CoreSearchProvider(BaseSearchProvider):
    """
    Search core.models.machine ProviderMachine.
    """

    def search(identity, query):
        return ProviderMachine.objects.filter(
            Q(machine__private=True, created_by_identity=identity)
            | Q(machine__private=False, provider=identity.provider),
            Q(machine__tags__name__icontains=query)
            | Q(machine__tags__description__icontains=query)
            | Q(machine__name__icontains=query)
            | Q(machine__description__icontains=query))
