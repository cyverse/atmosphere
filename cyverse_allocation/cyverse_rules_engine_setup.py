from business_rules.actions import BaseActions, rule_action
from business_rules.fields import FIELD_NUMERIC
from business_rules.variables import BaseVariables, boolean_rule_variable, numeric_rule_variable, string_rule_variable

from core.models.allocation_source import AllocationSource,AllocationSourceSnapshot
from core.models.event_table import EventTable


class CyverseTestRenewalVariables(BaseVariables):
    def __init__(self, allocation_source, current_time, last_renewal_event_date):
        self.allocation_source = allocation_source
        self.current_time = current_time
        self.last_renewal_event_date = last_renewal_event_date

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
        return (
            self.current_time - self.last_renewal_event_date).days


class CyverseTestRenewalActions(BaseActions):
    def __init__(self, allocation_source, current_time):
        if not isinstance(allocation_source, AllocationSource):
            raise Exception('Please provide Allocation Source instance for renewal')
        self.allocation_source = allocation_source
        self.current_time = current_time

    @rule_action(params={"compute_allowed": FIELD_NUMERIC})
    def renew_allocation_source(self, compute_allowed):
        source_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=self.allocation_source)
        if not source_snapshot:
            raise Exception('Allocation Source %s cannot be renewed because no snapshot is available' % (
                self.allocation_source.name))
        source_snapshot = source_snapshot.last()
        remaining_compute = 0 if source_snapshot.compute_allowed - source_snapshot.compute_used < 0 else source_snapshot.compute_allowed - source_snapshot.compute_used
        total_compute_allowed = float(remaining_compute + compute_allowed)

        # fire renewal event

        renewal_strategy = self.allocation_source.renewal_strategy
        allocation_source_name = self.allocation_source.name
        allocation_source_uuid = self.allocation_source.uuid

        payload = {
            "uuid": str(allocation_source_uuid),
            "renewal_strategy": renewal_strategy,
            "allocation_source_name": allocation_source_name,
            "compute_allowed": total_compute_allowed
        }

        EventTable.objects.create(name='allocation_source_created_or_renewed',
                                  payload=payload,
                                  entity_id=allocation_source_name,
                                  timestamp=self.current_time)

    @rule_action()
    def cannot_renew_allocation_source(self):
        pass


def parse_cyverse_rules(renewal_strategies):
    cyverse_rules = []
    for strategy, config in renewal_strategies.iteritems():
        rule = {}
        name, compute_allowed, renewed_in_days = strategy, \
                                                 config['compute_allowed'], \
                                                 config['renewed_in_days']
        conditions = _create_conditions_for(name, renewed_in_days)
        actions = _create_actions_for(compute_allowed, renewed_in_days)
        rule['conditions'] = {"all": conditions}
        rule['actions'] = actions
        cyverse_rules.append(rule)

    return cyverse_rules


def _create_conditions_for(name, renewed_in_days):
    conditions = []

    # condition 1
    conditions.append({"name": "renewal_strategy",
                       "operator": "equal_to",
                       "value": name})

    # condition 2
    conditions.append({"name": "is_valid",
                       "operator": "is_true",
                       "value": True})

    # condition 3 if strategy is renewable
    if renewed_in_days > 0:
        conditions.append({"name": "days_since_renewed",
                           "operator": "greater_than_or_equal_to",
                           "value": renewed_in_days})

    return conditions


def _create_actions_for(compute_allowed, renewed_in_days):
    actions = []

    if renewed_in_days > 0:
        actions.append({"name": "renew_allocation_source",
                        "params": {"compute_allowed": compute_allowed}
                        })

    else:
        actions.append({"name": "cannot_renew_allocation_source"})

    return actions


# RENEWAL STRATEGY CONFIGURATION
renewal_strategies = {

    'default': {'id': 1,
                'compute_allowed': 250,
                'renewed_in_days': 3,
                'external': False},

    'bi-weekly': {'id': 2,
                  'compute_allowed': 150,
                  'renewed_in_days': 14,
                  'external': True},

    'workshop': {'id': 3,
                 'compute_allowed': 0,
                 'renewed_in_days': 0,
                 'external': False},

    'custom': {'id': 4,
               'compute_allowed': 0,
               'renewed_in_days': 0,
               'external': True},
}

# MAIN RULES JSON
cyverse_rules = parse_cyverse_rules(renewal_strategies)
