from business_rules.variables import BaseVariables, boolean_rule_variable, numeric_rule_variable
from business_rules.actions import BaseActions, rule_action
from dateutil.parser import parse
from core.models.allocation_source import AllocationSourceSnapshot


class CyverseTestSupplementVariables(BaseVariables):
    def __init__(self, allocation_source, supplement_requested, current_time):
        self.allocation_source = allocation_source
        self.supplement_requested = supplement_requested
        self.current_time = current_time

    @boolean_rule_variable
    def is_valid(self):
        if self.allocation_source.end_date > parse(self.current_time):
            return True
        return False

    @boolean_rule_variable
    def is_at_full_capacity(self):
        if self.allocation_source.compute_allowed > AllocationSourceSnapshot.objects.get(allocation_source = self.allocation_source).compute_used:
            return True
        return False

    @numeric_rule_variable
    def supplement_requested(self):
        return self.supplement_requested

class CyverseTestSupplementActions(BaseActions):
    def __init__(self, allocation_source,supplement_requested):
        self.allocation_source = allocation_source
        self.supplement_requested = supplement_requested

    @rule_action()
    def supplement_allocation_source(self):
        self.allocation_source.compute_allowed += self.supplement_requested
        self.allocation_source.save()


cyverse_rules = [
    #  if isValid(allocation_source) && supplement>0
    {"conditions": {"all": [
        {"name": "is_valid",
         "operator": "equal_to",
         "value": True,
         },
        {"name": "supplement_requested",
         "operator": "greater_than",
         "value": 0,
         },
    ]},
        "actions": [
            {"name": "supplement_allocation_source",
             },
        ],
    },
]
