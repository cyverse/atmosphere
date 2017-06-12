import django
from threepio import logger

import atmosphere.plugins.quota.default_quota
from jetstream.allocation import TASAPIDriver, fill_user_allocation_source_for
from jetstream.exceptions import TASAPIException


class JetstreamSpecialAllocationQuota(atmosphere.plugins.quota.default_quota.DefaultQuotaPlugin):
    def get_default_quota(self, user, provider):
        """
        If a user is only in a special allocation, then give them a reduced quota
        """
        driver = TASAPIDriver()
        special_allocation_sources = getattr(django.conf.settings, 'SPECIAL_ALLOCATION_SOURCES', {})
        default_quota = None
        try:
            project_allocations = fill_user_allocation_source_for(driver, user)
            if project_allocations and len(project_allocations) == 1 and project_allocations[
                0].name in special_allocation_sources:
                import core.models
                sub_allocation_quota = special_allocation_sources[project_allocations[0].name].get('default_quota')
                if sub_allocation_quota:
                    default_quota = core.models.Quota.objects.get_or_create(**sub_allocation_quota)[0]
            return default_quota
        except TASAPIException:
            logger.exception('Could not validate user: %s' % user)
            return None
