from business_rules.actions import BaseActions, rule_action
from business_rules.fields import FIELD_NUMERIC, FIELD_TEXT
from business_rules.variables import BaseVariables, boolean_rule_variable, numeric_rule_variable, string_rule_variable

from core.models.allocation_source import AllocationSource
from core.models.event_table import EventTable
from django.conf import settings


class CyverseTestRenewalVariables(BaseVariables):
    def __init__(
        self, allocation_source, current_time, last_renewal_event_date
    ):
        self.allocation_source = allocation_source
        self.current_time = current_time
        self.last_renewal_event_date = last_renewal_event_date

    @string_rule_variable
    def renewal_strategy(self):
        return self.allocation_source.renewal_strategy

    @boolean_rule_variable
    def is_valid(self):
        if (
            not self.allocation_source.end_date
            or (self.allocation_source.end_date > self.current_time)
        ):
            return True
        return False

    @boolean_rule_variable
    def hard_coded_false(self):
        return False

    #
    # @boolean_rule_variable
    # def is_at_full_capacity(self):
    #     if self.allocation_source.compute_allowed > AllocationSource.objects.get(allocation_source = self.allocation_source).compute_used:
    #         return True
    #     return False

    @numeric_rule_variable
    def days_since_renewed(self):
        return (self.current_time - self.last_renewal_event_date).days

    @numeric_rule_variable
    def today_calendar_day(self):
        return self.current_time.day


class CyverseTestRenewalActions(BaseActions):
    def __init__(self, allocation_source, current_time):
        if not isinstance(allocation_source, AllocationSource):
            raise Exception(
                'Please provide Allocation Source instance for renewal'
            )
        self.allocation_source = allocation_source
        self.current_time = current_time

    @rule_action(
        params={
            "strategy_name": FIELD_TEXT,
            "compute_allowed": FIELD_NUMERIC
        }
    )
    def renew_allocation_source(self, strategy_name, compute_allowed):
        total_compute_allowed = compute_allowed

        # fire renewal event

        allocation_source_name = self.allocation_source.name
        allocation_source_uuid = self.allocation_source.uuid

        payload = {
            "uuid": str(allocation_source_uuid),
            "renewal_strategy": strategy_name,
            "allocation_source_name": allocation_source_name,
            "compute_allowed": total_compute_allowed
        }

        EventTable.objects.create(
            name='allocation_source_created_or_renewed',
            payload=payload,
            entity_id=allocation_source_name,
            timestamp=self.current_time
        )

    @rule_action()
    def cannot_renew_allocation_source(self):
        pass


def parse_cyverse_rules(renewal_strategies):
    new_cyverse_rules = []
    for strategy_name, strategy_config in renewal_strategies.iteritems():
        rule = {}
        conditions = _create_conditions_for(strategy_name, strategy_config)
        actions = _create_actions_for(strategy_name, strategy_config)
        rule['conditions'] = {"all": conditions}
        rule['actions'] = actions
        new_cyverse_rules.append(rule)

    return new_cyverse_rules


def _create_conditions_for(strategy_name, strategy_config):
    conditions = []
    period_type = strategy_config.get('period_type')
    period_param = strategy_config.get('period_param')

    if not period_type:
        # We don't automatically renew for strategies without a period. So add a dummy condition that should fail.
        conditions.append(
            {
                "name": "hard_coded_false",
                "operator": "is_true",
                "value": True
            }
        )
        return conditions

    # Does the Allocation Source renewal strategy match `strategy_name`?
    conditions.append(
        {
            "name": "renewal_strategy",
            "operator": "equal_to",
            "value": strategy_name
        }
    )

    # Is the Allocation Source valid? (Basically valid if it has not been end-dated.)
    conditions.append(
        {
            "name": "is_valid",
            "operator": "is_true",
            "value": True
        }
    )

    assert period_type in ['days', 'on_calendar_day']

    if period_type == 'on_calendar_day':
        calendar_day_to_renew_on = period_param
        assert type(
            calendar_day_to_renew_on
        ) == int, 'Invalid calendar day: Must be an integer'
        assert 0 < calendar_day_to_renew_on <= 31, 'Invalid calendar day: Must be an integer from 1 to 31'
        # TODO: What happens when the cron job doesn't fire on the first of the month?
        # Add a condition to check if it's been more than a month since last renewal?

        # Make sure it's been more than a day since we last renewed
        conditions.append(
            {
                "name": "days_since_renewed",
                "operator": "greater_than_or_equal_to",
                "value": 1
            }
        )
        conditions.append(
            {
                "name": "today_calendar_day",
                "operator": "equal_to",
                "value": calendar_day_to_renew_on
            }
        )

    if period_type == 'days':
        renewed_in_days = period_param
        assert type(
            renewed_in_days
        ) == int, 'Invalid number of days: Must be an integer'
        conditions.append(
            {
                "name": "days_since_renewed",
                "operator": "greater_than_or_equal_to",
                "value": renewed_in_days
            }
        )

    return conditions


def _create_actions_for(strategy_name, strategy_config):
    actions = []
    compute_allowed = strategy_config.get('compute_allowed', 0)
    period_type = strategy_config.get('period_type')

    if period_type is None:
        actions.append({"name": "cannot_renew_allocation_source"})
        return actions

    actions.append(
        {
            "name": "renew_allocation_source",
            "params":
                {
                    "strategy_name": strategy_name,
                    "compute_allowed": compute_allowed
                }
        }
    )

    return actions


# RENEWAL STRATEGY CONFIGURATION
renewal_strategies = {
    'default':
        {
            'id': 1,
            'compute_allowed': getattr(settings, 'ALLOCATION_SOURCE_COMPUTER_ALLOWED', 336),
            'period_type': 'on_calendar_day',
            'period_param': 1
        },
    'bi-weekly':
        {
            'id': 2,
            'compute_allowed': 84,
            'period_type': 'days',
            'period_param': 14
        },
    'workshop':
        {
            'id': 3,
            'compute_allowed': 0,
            'period_type': 'days',
            'period_param': 7
        },
    'custom':
        {
            'id': 4,
            'compute_allowed': 0,
            'period_type': None,
            'period_param': None
        },
}

# MAIN RULES JSON
cyverse_rules = parse_cyverse_rules(renewal_strategies)
