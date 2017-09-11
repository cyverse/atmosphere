Feature: Enforcing allocation usage on Jetstream
  - Prevent launching of an instance if not enough allocation
  - Send emails at various thresholds
  - Shelve instances when last threshold
  - Allow launching instances after allocation is reset/renewed (manually? Or trigger event?)

  Background: Some TAS API fixtures
    Given a dummy browser
    And a TAS API driver
    And a current time of '2017-02-15T05:00:00Z'
    And we clear the local cache
    And the following Atmosphere users
    # Note: Not many Atmosphere users yet - will be created later
      | username |
      | user207  |
#      | user208  |
#      | user209  |
#      | user210  |
#      | user211  |
    And the following XSEDE to TACC username mappings
    # Note: No tacc_username for `user207`, but there is one for `user210`
      | xsede_username | tacc_username |
      | user208        | tacc_user208  |
      | user209        | tacc_user209  |
      | user210        | tacc_user210  |
      | user211        | tacc_user211  |
    And the following TAS projects
      | id    | chargeCode   |
      | 29444 | TG-BIO150062 |
      | 29456 | TG-TRA160003 |
      | 29567 | TG-ASC160018 |
    And the following TAS allocations
      | id    | projectId | project      | computeAllocated | computeUsed | start                | end                  | status   | resource  |
      | 38229 | 29444     | TG-BIO150062 | 1000000          | 781768.01   | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active   | Jetstream |
      | 38271 | 29456     | TG-TRA160003 | 500000           | 583803.28   | 2016-01-22T06:00:00Z | 2017-01-21T06:00:00Z | Inactive | Jetstream |
      | 45184 | 29456     | TG-TRA160003 | 600000           | 87914.06    | 2017-01-22T06:00:00Z | 2018-01-21T06:00:00Z | Active   | Jetstream |
      | 55184 | 29456     | TG-TRA160003 | 700000           | 0           | 2018-01-22T06:00:00Z | 2019-01-21T06:00:00Z | Approved | Jetstream |
      | 65186 | 29567     | TG-ASC160018 | 5000000          | 3000001.1   | 2017-01-22T06:00:00Z | 2018-01-21T06:00:00Z | Active   | Jetstream |
    And the following TACC usernames for TAS projects
      | project      | tacc_usernames            |
      | TG-BIO150062 | tacc_user208,tacc_user209 |
      | TG-TRA160003 | tacc_user209,tacc_user211 |
      | TG-ASC160018 | tacc_user210,tacc_user211 |
    When we get all projects
    Then we should have the following local projects
      | id    | chargeCode   |
      | 29444 | TG-BIO150062 |
      | 29456 | TG-TRA160003 |
      | 29567 | TG-ASC160018 |
    And we should have the following local allocations
      | id    | projectId | project      | computeAllocated | computeUsed | start                | end                  | status   | resource  |
      | 38229 | 29444     | TG-BIO150062 | 1000000          | 781768.01   | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active   | Jetstream |
      | 38271 | 29456     | TG-TRA160003 | 500000           | 583803.28   | 2016-01-22T06:00:00Z | 2017-01-21T06:00:00Z | Inactive | Jetstream |
      | 45184 | 29456     | TG-TRA160003 | 600000           | 87914.06    | 2017-01-22T06:00:00Z | 2018-01-21T06:00:00Z | Active   | Jetstream |
      | 55184 | 29456     | TG-TRA160003 | 700000           | 0           | 2018-01-22T06:00:00Z | 2019-01-21T06:00:00Z | Approved | Jetstream |
      | 65186 | 29567     | TG-ASC160018 | 5000000          | 3000001.1   | 2017-01-22T06:00:00Z | 2018-01-21T06:00:00Z | Active   | Jetstream |
    When we fill user allocation sources from TAS
    Then we should have the following local username mappings
      | key | value |
    # Note: There should be no events until an Atmosphere user account exists locally and we fill user allocations
    And we should have the following events
      | entity_id | name | payload | timestamp |


  @skip-if-cyverse
  Scenario: Test basic enforcing
    Given "Admin" as the persona
    When I set "username" to "admin"
    And I set "password" to "very-clever-admin-password"
    And we create a new admin user
    And we create a provider "MockProvider"
    And we create an identity for the current persona on provider "MockProvider"
    And we make the current identity the admin on provider "MockProvider"

    Given "user208" as the persona
    When I set "username" to "user208"
    And I set "password" to "some-very-long-string"

    Given a current time of '2017-02-16T06:00:00Z'
    When I log in with valid XSEDE project required and default quota plugin enabled
    And we create an account for the current persona on provider "MockProvider"
    Then I should have the following quota on provider "MockProvider"
      | key               | value |
      | cpu               | 16    |
      | memory            | 128   |
      | storage           | 10    |
      | storage_count     | 10    |
      | instance_count    | 10    |
      | snapshot_count    | 10    |
      | floating_ip_count | 10    |
      | port_count        | 10    |
    And we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user208             | TG-BIO150062      |

    When we fill user allocation sources from TAS
    Then we should have the following local username mappings
      | key     | value        |
      | user208 | tacc_user208 |
    And we should have the following events
      | entity_id | name                                      | payload                                                                                                                                          | timestamp                |
      |           | allocation_source_created_or_renewed      | {"allocation_source_name": "TG-BIO150062", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": 1000000} | 2017-02-16 06:00:00+0000 |
      |           | allocation_source_compute_allowed_changed | {"allocation_source_name": "TG-BIO150062", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": 1000000} | 2017-02-16 06:00:00+0000 |
      | user208   | user_allocation_source_created            | {"allocation_source_name": "TG-BIO150062"}                                                                                                       | 2017-02-16 06:00:00+0000 |


    When we update snapshots
    Then we should have the following allocation source snapshots
      | name         | compute_used | compute_allowed |
      | TG-BIO150062 | 781768.01    | 1000000         |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user208             | TG-BIO150062      | 0.000        | 0.000     |

    When I get my allocation sources from the API I should see
      | name         | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | TG-BIO150062 | 1000000         | 2017-02-16 06:00:00+0000 | None     | 781768.010   | 0.000            | 2017-02-16 06:00:00+0000 | default          | 0.000             | 0.000          | 2017-02-16 06:00:00+0000 |

    Given a current time of '2017-02-16T07:00:00Z'
    When we create a provider machine for current persona
    And we create an active instance
    And we get the details for the active instance via the API
    Then the API response code is 200
    # TODO: And the active instance is not associated with an allocation source

    # Assign the allocation source to the instance
    Given a current time of '2017-02-16T07:01:00Z' with tick = False
    When I assign allocation source "TG-BIO150062" to active instance
    Then the API response code is 201
    And I set "instance01" to another variable "active_instance"
    # TODO: And the active instance is associated with allocation source "TG-BIO150062"
    Then we should have the following events
      | entity_id | name                                      | payload                                                                                                                                          | timestamp                |
      |           | allocation_source_created_or_renewed      | {"allocation_source_name": "TG-BIO150062", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": 1000000} | 2017-02-16 06:00:00+0000 |
      |           | allocation_source_compute_allowed_changed | {"allocation_source_name": "TG-BIO150062", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": 1000000} | 2017-02-16 06:00:00+0000 |
      | user208   | user_allocation_source_created            | {"allocation_source_name": "TG-BIO150062"}                                                                                                       | 2017-02-16 06:00:00+0000 |
      | user208   | instance_allocation_source_changed        | {"instance_id": "{instance01.provider_alias}", "allocation_source_name": "TG-BIO150062"}                                                         | 2017-02-16 07:01:00+0000 |


    # Check usage immediately after launching instance
    Given a current time of '2017-02-16T07:02:00Z' with tick = False
    When we update snapshots
    Then we should have the following allocation source snapshots
      | name         | compute_used | compute_allowed |
      | TG-BIO150062 | 781768.01    | 1000000         |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user208             | TG-BIO150062      | 0.020        | 1.000     |
    When I get my allocation sources from the API I should see
      | name         | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | TG-BIO150062 | 1000000         | 2017-02-16 06:00:00+0000 | None     | 781768.010   | 1.000            | 2017-02-16 07:02:00+0000 | default          | 0.02              | 1.000          | 2017-02-16 07:02:00+0000 |

    # Check usage after an hour
    Given a current time of '2017-02-16T08:00:00Z' with tick = False
    When we update snapshots
    Then we should have the following allocation source snapshots
      | name         | compute_used | compute_allowed |
      | TG-BIO150062 | 781768.01    | 1000000         |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user208             | TG-BIO150062      | 0.980        | 1.000     |


    # TODO: Fix compute_used & burn_rate
    When I get my allocation sources from the API I should see
      | name         | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | TG-BIO150062 | 1000000         | 2017-02-16 06:00:00+0000 | None     | 781768.010   | 1.000            | 2017-02-16 08:00:00+0000 | default          | 0.980             | 1.000          | 2017-02-16 08:00:00+0000 |

