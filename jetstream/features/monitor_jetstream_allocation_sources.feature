Feature: Monitor Jetstream Allocation Sources
  Monitoring the TACC API for Jetstream allocation sources

  Background: Some TAS API fixtures
    Given a TAS API driver
    And a current time of '2017-02-15T05:00:00Z'
    And we clear the local cache
    And the following Atmosphere users
      | username |
      | user107  |
      | user108  |
      | user109  |
      | user110  |
      | user111  |
    And the following XSEDE to TACC username mappings
    # Note: No tacc_username for `user107`
      | xsede_username | tacc_username |
      | user108        | tacc_user108  |
      | user109        | tacc_user109  |
      | user110        | tacc_user110  |
      | user111        | tacc_user111  |
    And the following TAS projects
      | id    | chargeCode   |
      | 29444 | TG-BIO150062 |
      | 29456 | TG-TRA160003 |
    And the following TAS allocations
      | id    | projectId | project      | computeAllocated | computeUsed | start                | end                  | status   | resource  |
      | 38229 | 29444     | TG-BIO150062 | 1000000          | 781768.01   | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active   | Jetstream |
      | 38271 | 29456     | TG-TRA160003 | 500000           | 583803.28   | 2016-01-22T06:00:00Z | 2017-01-21T06:00:00Z | Inactive | Jetstream |
      | 45184 | 29456     | TG-TRA160003 | 600000           | 87914.06    | 2017-01-22T06:00:00Z | 2018-01-21T06:00:00Z | Active   | Jetstream |
      | 55184 | 29456     | TG-TRA160003 | 700000           | 0           | 2018-01-22T06:00:00Z | 2019-01-21T06:00:00Z | Approved | Jetstream |
    And the following TACC usernames for TAS projects
      | project_id | tacc_usernames            |
      | 29444      | tacc_user108,tacc_user109 |
      | 29456      | tacc_user109,tacc_user111 |


  Scenario: Get all projects
    When we get all projects
    Then we should have the following local projects
      | id    | chargeCode   |
      | 29444 | TG-BIO150062 |
      | 29456 | TG-TRA160003 |
    And we should have the following local allocations
      | id    | projectId | project      | computeAllocated | computeUsed | start                | end                  | status   | resource  |
      | 38229 | 29444     | TG-BIO150062 | 1000000          | 781768.01   | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active   | Jetstream |
      | 38271 | 29456     | TG-TRA160003 | 500000           | 583803.28   | 2016-01-22T06:00:00Z | 2017-01-21T06:00:00Z | Inactive | Jetstream |
      | 45184 | 29456     | TG-TRA160003 | 600000           | 87914.06    | 2017-01-22T06:00:00Z | 2018-01-21T06:00:00Z | Active   | Jetstream |
      | 55184 | 29456     | TG-TRA160003 | 700000           | 0           | 2018-01-22T06:00:00Z | 2019-01-21T06:00:00Z | Approved | Jetstream |


  Scenario: Fill user allocation sources
    When we get all projects
    And we fill user allocation sources from TAS
    Then we should have the following local username mappings
      | key     | value        |
      | user108 | tacc_user108 |
      | user109 | tacc_user109 |
      | user110 | tacc_user110 |
      | user111 | tacc_user111 |
    And we should have the following local projects
      | id    | chargeCode   |
      | 29444 | TG-BIO150062 |
      | 29456 | TG-TRA160003 |
    And we should have the following allocation sources
      | name         | compute_allowed |
      | TG-BIO150062 | 1000000         |
      | TG-TRA160003 | 600000          |
    And we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-BIO150062      |
      | user109             | TG-BIO150062      |
      | user109             | TG-TRA160003      |
      | user111             | TG-TRA160003      |


  Scenario: Remove user from allocation source
    When we get all projects
    And we fill user allocation sources from TAS
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-BIO150062      |
      | user109             | TG-BIO150062      |
      | user109             | TG-TRA160003      |
      | user111             | TG-TRA160003      |
    Given a current time of '2017-02-17T05:00:00Z'
    And the following TACC usernames for TAS projects
      | project_id | tacc_usernames            |
      | 29444      | tacc_user108              |
      | 29456      | tacc_user109,tacc_user111 |
    When we fill user allocation sources from TAS
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-BIO150062      |
      | user109             | TG-TRA160003      |
      | user111             | TG-TRA160003      |
    Given a current time of '2017-02-19T05:00:00Z'
    And the following TACC usernames for TAS projects
      | project_id | tacc_usernames |
      | 29444      | tacc_user108   |
      | 29456      | tacc_user111   |
    When we fill user allocation sources from TAS
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-BIO150062      |
      | user111             | TG-TRA160003      |


  Scenario: Calculate allocation source snapshots
    When we get all projects
    And we fill user allocation sources from TAS
    And we update snapshots
    Then we should have the following allocation source snapshots
      | name         | compute_used |
      | TG-BIO150062 | 781768.010   |
      | TG-TRA160003 | 87914.060    |


  @skip
  Scenario: Generate reports