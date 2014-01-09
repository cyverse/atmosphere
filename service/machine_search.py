"""
Provide pluggable machine search for Atmosphere.

"""


from abc import ABCMeta, abstractmethod
import operator

from django.db.models import Q

from core.models.machine import compare_core_machines, filter_core_machine,\
    convert_esh_machine, update_machine_metadata,\
    ProviderMachine


def search(providers, identity, query):
    return reduce(operator.or_, [p.search(identity, query) for p in providers])


class BaseSearchProvider():
    """
    BaseSearchProvider lists a basic set of expected functionality for
    search providers.
    """

    __metaclass__ = ABCMeta

    @classmethod
    @abstractmethod
    def search(cls, identity, query):
        raise NotImplementedError


class CoreSearchProvider(BaseSearchProvider):
    """
    Search core.models.machine ProviderMachine.
    """

    @classmethod
    def search(cls, identity, query):
        return ProviderMachine.objects.filter(
            # Privately owned OR public machines
            Q(application__private=True, created_by_identity=identity)
            | Q(application__private=False, provider=identity.provider),
            # AND query matches on:
            # app tag name OR
            # app tag desc OR
            # app name OR
            # app desc
            Q(application__tags__name__icontains=query)
            | Q(application__tags__description__icontains=query)
            | Q(application__name__icontains=query)
            | Q(application__description__icontains=query))
