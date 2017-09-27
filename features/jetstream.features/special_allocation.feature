@skip-if-cyverse
Feature: Special Allocations
  Test special (_sub_) allocations

  Background: Some TAS API fixtures
    Given a dummy browser
    And a TAS API driver
    And a current time of '2017-02-15T05:00:00Z'
    And we clear the local cache
    And the following Atmosphere users
    # Note: Not many Atmosphere users yet - will be created later
      | username |
      | user107  |
#      | user108  |
#      | user109  |
#      | user110  |
#      | user111  |
    And the following XSEDE to TACC username mappings
    # Note: No tacc_username for `user107`, but there is one for `user110`
      | xsede_username | tacc_username |
      | user108        | tacc_user108  |
      | user109        | tacc_user109  |
      | user110        | tacc_user110  |
      | user111        | tacc_user111  |
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
      | TG-BIO150062 | tacc_user108,tacc_user109 |
      | TG-TRA160003 | tacc_user109,tacc_user111 |
      | TG-ASC160018 | tacc_user110,tacc_user111 |
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


  Scenario: When a user logs in for the first time, and they only have access to the special allocation (`user110`)
    Given "Admin" as the persona
    When I set "username" to "admin"
    And I set "password" to "very-clever-admin-password"
    And we create a new admin user
    And we create a provider "MockProvider"
    And we create an identity for the current persona on provider "MockProvider"
    And we make the current identity the admin on provider "MockProvider"

    Given "user110" as the persona
    When I set "username" to "user110"
    And I set "password" to "some-very-long-string"

    Given a current time of '2017-02-16T05:00:00Z'
    When I log in with valid XSEDE project required and default quota plugin enabled
    And we create an account for the current persona on provider "MockProvider"
    Then I should have the following quota on provider "MockProvider"
      | key               | value |
      | cpu               | 2     |
      | memory            | 128   |
      | storage           | 10    |
      | storage_count     | 1     |
      | instance_count    | 1     |
      | snapshot_count    | 1     |
      | floating_ip_count | -1    |
      | port_count        | -1    |
    And we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user110             | TG-ASC160018      |

    When we update snapshots
    Then we should have the following allocation source snapshots
      | name         | compute_used | compute_allowed |
      | TG-ASC160018 | 3000001.100  | 5000000         |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user110             | TG-ASC160018      | 0.000        | 0.000     |

    When I get my allocation sources from the API I should see
      | name         | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | TG-ASC160018 | 1000            | 2017-02-16 05:00:00+0000 | None     | 0.000        | 0.000            | 2017-02-16 05:00:00+0000 | default          | 0.000             | 0.000          | 2017-02-16 05:00:00+0000 |

    When we increase compute used by 500 for the user on "TG-ASC160018"
    Then we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user110             | TG-ASC160018      | 500.0        | 0.000     |

    When I get my allocation sources from the API I should see
      | name         | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | TG-ASC160018 | 1000            | 2017-02-16 05:00:00+0000 | None     | 500.000      | 0.000            | 2017-02-16 05:00:00+0000 | default          | 500.000           | 0.000          | 2017-02-16 05:00:00+0000 |
    And my time remaining on "TG-ASC160018" is 500
    When the user allocation snapshot for "user110" and "TG-ASC160018" is deleted
    Then we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
    And my time remaining on "TG-ASC160018" is -1
    And I should be over my allocation on "TG-ASC160018"
    And time remaining on allocation source "TG-ASC160018" is 1999998.9
    And allocation source "TG-ASC160018" is not over allocation

    When I get my allocation sources from the API I should see
      | name         | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated |
      | TG-ASC160018 | 1000            | 2017-02-16 05:00:00+0000 | None     | 0            | None             | 2017-02-16 05:00:00+0000 | default          | 0                 | None           | None                  |


  Scenario: When a user logs in for the first time, and they don't have access to the special allocation (`user108`)
    Given "Admin" as the persona
    When I set "username" to "admin"
    And I set "password" to "very-clever-admin-password"
    And we create a new admin user
    And we create a provider "MockProvider"
    And we create an identity for the current persona on provider "MockProvider"
    And we make the current identity the admin on provider "MockProvider"

    Given "user108" as the persona
    When I set "username" to "user108"
    And I set "password" to "some-very-long-string"

    Given a current time of '2017-02-16T05:00:00Z'
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
      | user108             | TG-BIO150062      |

    When we update snapshots
    Then we should have the following allocation source snapshots
      | name         | compute_used | compute_allowed |
      | TG-BIO150062 | 781768.01    | 1000000         |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user108             | TG-BIO150062      | 0.000        | 0.000     |

    When I get my allocation sources from the API I should see
      | name         | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | TG-BIO150062 | 1000000         | 2017-02-16 05:00:00+0000 | None     | 781768.010   | 0.000            | 2017-02-16 05:00:00+0000 | default          | 0.000             | 0.000          | 2017-02-16 05:00:00+0000 |


  Scenario: When a user logs in for the first time, and they have access to the special allocation as well as another
  one (`user111`)
    Given "Admin" as the persona
    When I set "username" to "admin"
    And I set "password" to "very-clever-admin-password"
    And we create a new admin user
    And we create a provider "MockProvider"
    And we create an identity for the current persona on provider "MockProvider"
    And we make the current identity the admin on provider "MockProvider"

    Given "user111" as the persona
    When I set "username" to "user111"
    And I set "password" to "some-very-long-string"

    Given a current time of '2017-02-16T05:00:00Z'
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
      | user111             | TG-TRA160003      |
      | user111             | TG-ASC160018      |

    When we update snapshots
    Then we should have the following allocation source snapshots
      | name         | compute_used | compute_allowed |
      | TG-TRA160003 | 87914.06     | 600000          |
      | TG-ASC160018 | 3000001.100  | 5000000         |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user111             | TG-TRA160003      | 0.000        | 0.000     |
      | user111             | TG-ASC160018      | 0.000        | 0.000     |

    When I get my allocation sources from the API I should see
      | name         | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | TG-ASC160018 | 1000            | 2017-02-16 05:00:00+0000 | None     | 0.000        | 0.000            | 2017-02-16 05:00:00+0000 | default          | 0                 | 0.000          | 2017-02-16 05:00:00+0000 |
      | TG-TRA160003 | 600000          | 2017-02-16 05:00:00+0000 | None     | 87914.060    | 0.000            | 2017-02-16 05:00:00+0000 | default          | 0                 | 0.000          | 2017-02-16 05:00:00+0000 |

