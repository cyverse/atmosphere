from business_rules.variables import BaseVariables, boolean_rule_variable, numeric_rule_variable, string_rule_variable
from business_rules.actions import BaseActions, rule_action
from business_rules.fields import FIELD_NUMERIC
from dateutil.parser import parse
from core.models.allocation_source import AllocationSource,AllocationSourceSnapshot
from core.models.event_table import EventTable


class CyverseTestRenewalVariables(BaseVariables):
    def __init__(self, allocation_source, current_time):
        self.allocation_source = allocation_source
        self.current_time = current_time

    @string_rule_variable
    def renewal_strategy(self):
        return self.allocation_source.renewal_strategy

    @boolean_rule_variable
    def is_valid(self):
        if (not self.allocation_source.end_date or (self.allocation_source.end_date > self.current_time)):
            return True
        return False
    #
    # @boolean_rule_variable
    # def is_at_full_capacity(self):
    #     if self.allocation_source.compute_allowed > AllocationSource.objects.get(allocation_source = self.allocation_source).compute_used:
    #         return True
    #     return False

    @numeric_rule_variable
    def days_since_renewed(self):

        source_id = self.allocation_source.uuid
        last_renewal_event = EventTable.objects.filter(
             name='allocation_source_renewed',
             payload__source_id__exact=source_id).order_by('timestamp')
        if not last_renewal_event:
            return (self.current_time - self.allocation_source.start_date).days
        return (last_renewal_event.last().timestamp - self.current_time).days



class CyverseTestRenewalActions(BaseActions):
    def __init__(self, allocation_source,current_time):
        if not isinstance(allocation_source, AllocationSource):
            raise Exception('Please provide Allocation Source instance for renewal')
        self.allocation_source = allocation_source
        self.current_time = current_time

    @rule_action(params={"compute_allowed": FIELD_NUMERIC})
    def renew_allocation_source(self,compute_allowed):
        source_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=self.allocation_source)
        if not source_snapshot:
            raise Exception('Allocation Source %s cannot be renewed because no snapshot is available'%(self.allocation_source.name))
        source_snapshot = source_snapshot.last()
        remaining_compute = 0 if source_snapshot.compute_allowed - source_snapshot.compute_used < 0 else source_snapshot.compute_allowed - source_snapshot.compute_used
        source_snapshot.compute_used = 0
        total_compute_allowed = float(remaining_compute + compute_allowed)
        source_snapshot.compute_allowed = total_compute_allowed
        source_snapshot.updated = self.current_time
        source_snapshot.save()

        # fire renewal event

        source_id = self.allocation_source.uuid

        payload = {
            "source_id" : source_id,
            "name" : self.allocation_source.name,
            "compute_allowed" : total_compute_allowed
        }

        EventTable.objects.create(name='allocation_source_renewed',
                                  payload=payload,
                                  entity_id=payload["source_id"],
                                  timestamp=self.current_time)

    @rule_action()
    def cannot_renew_allocation_source(self):
        pass

cyverse_rules = [
    #if strategy_name == 'default' AND isValid(allocation_source) AND days_since_renewed >= 30 THEN renew
    {"conditions": {"all": [
        {"name": "renewal_strategy",
         "operator": "equal_to",
         "value": 'default',
         },
        {"name": "is_valid",
         "operator": "is_true",
         "value": True
         },
        {"name": "days_since_renewed",
         "operator": "greater_than_or_equal_to",
         "value": 3,
         },
    ]},
        "actions": [
            {"name": "renew_allocation_source",
             "params": {"compute_allowed": 250}
             },
        ],
    },

    #if strategy_name == 'workshop' THEN cannot renew
    {"conditions": {"all": [
        {"name": "renewal_strategy",
         "operator": "equal_to",
         "value": 'workshop',
         },
    ]},
        "actions": [
            {"name": "cannot_renew_allocation_source",
             },
        ],
    },

    #if strategy_name == 'bi-weekly' AND isValid(allocation_source) AND days_since_renewed >= 14 THEN renew
    {"conditions": {"all": [
        {"name": "renewal_strategy",
         "operator": "equal_to",
         "value": 'bi-weekly',
         },
        {"name": "is_valid",
         "operator": "is_true",
         "value": True
         },
        {"name": "days_since_renewed",
         "operator": "greater_than_or_equal_to",
         "value": 14,
         },
    ]},
        "actions": [
            {"name": "renew_allocation_source",
             "params": {"compute_allowed": 150}
             },
        ],
    },

]
