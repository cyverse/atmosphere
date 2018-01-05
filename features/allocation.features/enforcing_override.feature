@skip-if-jetstream
Feature: Override enforcing allocation usage on CyVerse

  Background:
    Given a dummy browser
    And a current time of '2017-02-15T05:00:00Z' with tick = False
    And "Admin" as the persona
    When I set "username" to "admin"
    And I set "password" to "very-clever-admin-password"
    And we create a new admin user
    And we create a provider "MockProvider"
    And we create an identity for the current persona on provider "MockProvider"
    And we make the current identity the admin on provider "MockProvider"

  Scenario Outline: Override enforcement behavior for individual allocation sources
    Given "anybody" as the persona
    When I set "username" to "<username>"
    And I set "password" to "some-very-long-string"
    And we create a new user
    Given a current time of '2017-02-16T06:00:00Z' with tick = False
    When I log in
    And we create an identity for the current persona on provider "MockProvider"
    And we ensure that the user has an allocation source
    And I set "allocation_source" to allocation source with name "<username>"
    And I set "allocation_source_uuid" to attribute "uuid" of "allocation_source"
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source   |
      | <username>          | <allocation_source> |
    And we should have the following events
      | entity_id           | name                                 | payload                                                                                                                                                    | timestamp                |
      | <allocation_source> | allocation_source_created_or_renewed | {"renewal_strategy": "default", "uuid": "{allocation_source_uuid}", "allocation_source_name": "<allocation_source>", "compute_allowed": <compute_allowed>} | 2017-02-16 06:00:00+0000 |
      | <username>          | user_allocation_source_created       | {"allocation_source_name": "<username>"}                                                                                                                   | 2017-02-16 06:00:00+0000 |

    Given a current time of '<start_date>' with tick = False
    When we create a provider machine for current persona
    And we create an active instance
    And I assign allocation source "<allocation_source>" to active instance

    Given a current time of '<end_date>' with tick = False
    When we update CyVerse snapshots
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
      | user801  | user801           | NO_OVERRIDE    | 168             | 2017-02-16T07:00:00Z | 2017-02-17T07:00:00Z | 24           | No      |
      | user802  | user802           | NEVER_ENFORCE  | 168             | 2017-02-16T07:00:00Z | 2017-02-17T07:00:00Z | 24           | No      |
      | user803  | user803           | ALWAYS_ENFORCE | 168             | 2017-02-16T07:00:00Z | 2017-02-17T07:00:00Z | 24           | Yes     |
      | user804  | user804           | NO_OVERRIDE    | 168             | 2017-02-16T07:00:00Z | 2017-02-24T07:00:00Z | 192          | Yes     |
      | user805  | user805           | NEVER_ENFORCE  | 168             | 2017-02-16T07:00:00Z | 2017-02-24T07:00:00Z | 192          | No      |
      | user806  | user806           | ALWAYS_ENFORCE | 168             | 2017-02-16T07:00:00Z | 2017-02-24T07:00:00Z | 192          | Yes     |
