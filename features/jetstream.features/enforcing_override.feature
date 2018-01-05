@skip-if-cyverse
Feature: Override enforcing allocation usage on Jetstream

  Scenario Outline: Override enforcement behavior for individual allocation sources
    Given a dummy browser
    And a TAS API driver
    And a current time of '2017-02-15T05:00:00Z'
    And we clear the local cache
    And the following Atmosphere users
      | username |
    And the following XSEDE to TACC username mappings
      | xsede_username | tacc_username   |
      | <username>     | tacc_<username> |
    And the following TAS projects
      | id    | chargeCode          |
      | 29444 | <allocation_source> |
    And the following TAS allocations
      | id    | projectId | project             | computeAllocated  | computeUsed | start                | end                  | status | resource  |
      | 38229 | 29444     | <allocation_source> | <compute_allowed> | 0           | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active | Jetstream |
    And the following TACC usernames for TAS projects
      | project             | tacc_usernames  |
      | <allocation_source> | tacc_<username> |
    When we get all projects
    Then we should have the following local projects
      | id    | chargeCode          |
      | 29444 | <allocation_source> |
    And we should have the following local allocations
      | id    | projectId | project             | computeAllocated  | computeUsed | start                | end                  | status | resource  |
      | 38229 | 29444     | <allocation_source> | <compute_allowed> | 0           | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active | Jetstream |
    When we fill user allocation sources from TAS
    Then we should have the following local username mappings
      | key | value |
    And we should have the following events
      | entity_id | name | payload | timestamp |


    Given "Admin" as the persona
    When I set "username" to "admin"
    And I set "password" to "very-clever-admin-password"
    And we create a new admin user
    And we create a provider "MockProvider"
    And we create an identity for the current persona on provider "MockProvider"
    And we make the current identity the admin on provider "MockProvider"

    Given "<username>" as the persona
    When I set "username" to "<username>"
    And I set "password" to "some-very-long-string"

    Given a current time of '2017-02-16T06:00:00Z' with tick = False
    When I log in with valid XSEDE project required and default quota plugin enabled
    And we create an account for the current persona on provider "MockProvider"
    And I set "allocation_source" to allocation source with name "<allocation_source>"
    And I set "allocation_source_uuid" to attribute "uuid" of "allocation_source"
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source   |
      | <username>          | <allocation_source> |
    And we should have the following events
      | entity_id  | name                                      | payload                                                                                                                                                           | timestamp                |
      |            | allocation_source_created_or_renewed      | {"allocation_source_name": "<allocation_source>", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": <compute_allowed>} | 2017-02-16 06:00:00+0000 |
      |            | allocation_source_compute_allowed_changed | {"allocation_source_name": "<allocation_source>", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": <compute_allowed>} | 2017-02-16 06:00:00+0000 |
      | <username> | user_allocation_source_created            | {"allocation_source_name": "<allocation_source>"}                                                                                                                 | 2017-02-16 06:00:00+0000 |

    Given a current time of '<start_date>' with tick = False
    When we create a provider machine for current persona
    And we create an active instance
    And I assign allocation source "<allocation_source>" to active instance

    And I set "instance01" to another variable "active_instance"
    Then we should have the following "instance_allocation_source_changed" events
      | entity_id  | name                               | payload                                                                                         | timestamp                |
      | <username> | instance_allocation_source_changed | {"instance_id": "{instance01.provider_alias}", "allocation_source_name": "<allocation_source>"} | 2017-02-16 07:00:00+0000 |

    Given a current time of '<end_date>' with tick = False
    And the following TAS projects
      | id    | chargeCode          |
      | 29444 | <allocation_source> |
    And the following TAS allocations
      | id    | projectId | project             | computeAllocated  | computeUsed    | start                | end                  | status | resource  |
      | 38229 | 29444     | <allocation_source> | <compute_allowed> | <compute_used> | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active | Jetstream |
    When we update snapshots
    Then we should have the following allocation source snapshots
      | name                | compute_used   | compute_allowed   |
      | <allocation_source> | <compute_used> | <compute_allowed> |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source   | compute_used   | burn_rate |
      | <username>          | <allocation_source> | <compute_used> | 1.000     |
    When the `monitor_allocation_sources` scheduled task is run with settings
      | allocation_source   | override   |
      | <allocation_source> | <override> |
    Then `allocation_source_overage_enforcement_for_user` was called as follows
      | username   | allocation_source   | called    |
      | <username> | <allocation_source> | <enforce> |

    Examples:
      | username | allocation_source | override       | compute_allowed | start_date           | end_date             | compute_used | enforce |
      | user901  | TG-BIO150091      | NO_OVERRIDE    | 168             | 2017-02-16T07:00:00Z | 2017-02-17T07:00:00Z | 24           | No      |
      | user902  | TG-BIO150092      | NEVER_ENFORCE  | 168             | 2017-02-16T07:00:00Z | 2017-02-17T07:00:00Z | 24           | No      |
      | user903  | TG-BIO150093      | ALWAYS_ENFORCE | 168             | 2017-02-16T07:00:00Z | 2017-02-17T07:00:00Z | 24           | Yes     |
      | user904  | TG-BIO150094      | NO_OVERRIDE    | 168             | 2017-02-16T07:00:00Z | 2017-02-24T07:00:00Z | 192          | Yes     |
      | user905  | TG-BIO150095      | NEVER_ENFORCE  | 168             | 2017-02-16T07:00:00Z | 2017-02-24T07:00:00Z | 192          | No      |
      | user906  | TG-BIO150096      | ALWAYS_ENFORCE | 168             | 2017-02-16T07:00:00Z | 2017-02-24T07:00:00Z | 192          | Yes     |