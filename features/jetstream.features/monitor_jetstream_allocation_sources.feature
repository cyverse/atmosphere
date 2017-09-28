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
      | 29444 | TG-ENG150061 |
      | 29456 | TG-TRA160006 |
    And the following TAS allocations
      | id    | projectId | project      | computeAllocated | computeUsed | start                | end                  | status   | resource  |
      | 38229 | 29444     | TG-ENG150061 | 1000000          | 781768.01   | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active   | Jetstream |
      | 38271 | 29456     | TG-TRA160006 | 500000           | 583803.28   | 2016-01-22T06:00:00Z | 2017-01-21T06:00:00Z | Inactive | Jetstream |
      | 45184 | 29456     | TG-TRA160006 | 600000           | 87914.06    | 2017-01-22T06:00:00Z | 2018-01-21T06:00:00Z | Active   | Jetstream |
      | 55184 | 29456     | TG-TRA160006 | 700000           | 0           | 2018-01-22T06:00:00Z | 2019-01-21T06:00:00Z | Approved | Jetstream |
    And the following TACC usernames for TAS projects
      | project      | tacc_usernames            |
      | TG-ENG150061 | tacc_user108,tacc_user109 |
      | TG-TRA160006 | tacc_user109,tacc_user111 |


  Scenario: Get all projects
    When we get all projects
    Then we should have the following local projects
      | id    | chargeCode   |
      | 29444 | TG-ENG150061 |
      | 29456 | TG-TRA160006 |
    And we should have the following local allocations
      | id    | projectId | project      | computeAllocated | computeUsed | start                | end                  | status   | resource  |
      | 38229 | 29444     | TG-ENG150061 | 1000000          | 781768.01   | 2016-01-01T06:00:00Z | 2017-06-30T05:00:00Z | Active   | Jetstream |
      | 38271 | 29456     | TG-TRA160006 | 500000           | 583803.28   | 2016-01-22T06:00:00Z | 2017-01-21T06:00:00Z | Inactive | Jetstream |
      | 45184 | 29456     | TG-TRA160006 | 600000           | 87914.06    | 2017-01-22T06:00:00Z | 2018-01-21T06:00:00Z | Active   | Jetstream |
      | 55184 | 29456     | TG-TRA160006 | 700000           | 0           | 2018-01-22T06:00:00Z | 2019-01-21T06:00:00Z | Approved | Jetstream |


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
      | 29444 | TG-ENG150061 |
      | 29456 | TG-TRA160006 |
    And we should have the following allocation sources
      | name         | compute_allowed |
      | TG-ENG150061 | 1000000         |
      | TG-TRA160006 | 600000          |
    And we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-ENG150061      |
      | user109             | TG-ENG150061      |
      | user109             | TG-TRA160006      |
      | user111             | TG-TRA160006      |


  Scenario: Remove user from allocation source
    When we get all projects
    And we fill user allocation sources from TAS
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-ENG150061      |
      | user109             | TG-ENG150061      |
      | user109             | TG-TRA160006      |
      | user111             | TG-TRA160006      |
    Given a current time of '2017-02-17T05:00:00Z'
    And the following TACC usernames for TAS projects
      | project      | tacc_usernames            |
      | TG-ENG150061 | tacc_user108              |
      | TG-TRA160006 | tacc_user109,tacc_user111 |
    When we fill user allocation sources from TAS
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-ENG150061      |
      | user109             | TG-TRA160006      |
      | user111             | TG-TRA160006      |
    Given a current time of '2017-02-19T05:00:00Z'
    And the following TACC usernames for TAS projects
      | project      | tacc_usernames |
      | TG-ENG150061 | tacc_user108   |
      | TG-TRA160006 | tacc_user111   |
    When we fill user allocation sources from TAS
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-ENG150061      |
      | user111             | TG-TRA160006      |


  Scenario: Calculate allocation source snapshots
    When we get all projects
    And we fill user allocation sources from TAS
    And we update snapshots
    Then we should have the following allocation source snapshots
      | name         | compute_used | compute_allowed |
      | TG-ENG150061 | 781768.010   | 1000000         |
      | TG-TRA160006 | 87914.060    | 600000          |


  Scenario: Correct events, with no duplicates when checking twice
    When we get all projects
    Then we should have the following events
      | entity_id | name | payload | timestamp |
    When we fill user allocation sources from TAS
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-ENG150061      |
      | user109             | TG-ENG150061      |
      | user109             | TG-TRA160006      |
      | user111             | TG-TRA160006      |
    # TODO: `allocation_source_created_or_renewed` & `allocation_source_compute_allowed_changed` should have `entity_id`
    And we should have the following events
      | entity_id | name                                      | payload                                                                                                                                          | timestamp                |
      |           | allocation_source_created_or_renewed      | {"allocation_source_name": "TG-ENG150061", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": 1000000} | 2017-02-15 05:00:00+0000 |
      |           | allocation_source_compute_allowed_changed | {"allocation_source_name": "TG-ENG150061", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": 1000000} | 2017-02-15 05:00:00+0000 |
      | user108   | user_allocation_source_created            | {"allocation_source_name": "TG-ENG150061"}                                                                                                       | 2017-02-15 05:00:00+0000 |
      | user109   | user_allocation_source_created            | {"allocation_source_name": "TG-ENG150061"}                                                                                                       | 2017-02-15 05:00:00+0000 |
      |           | allocation_source_created_or_renewed      | {"allocation_source_name": "TG-TRA160006", "start_date": "2017-01-22T06:00:00Z", "end_date": "2018-01-21T06:00:00Z", "compute_allowed": 600000}  | 2017-02-15 05:00:00+0000 |
      |           | allocation_source_compute_allowed_changed | {"allocation_source_name": "TG-TRA160006", "start_date": "2017-01-22T06:00:00Z", "end_date": "2018-01-21T06:00:00Z", "compute_allowed": 600000}  | 2017-02-15 05:00:00+0000 |
      | user109   | user_allocation_source_created            | {"allocation_source_name": "TG-TRA160006"}                                                                                                       | 2017-02-15 05:00:00+0000 |
      | user111   | user_allocation_source_created            | {"allocation_source_name": "TG-TRA160006"}                                                                                                       | 2017-02-15 05:00:00+0000 |
    Given a current time of '2017-02-16T06:00:00Z'
    When we get all projects
    And we fill user allocation sources from TAS
    Then we should have the following user allocation sources
      | atmosphere_username | allocation_source |
      | user108             | TG-ENG150061      |
      | user109             | TG-ENG150061      |
      | user109             | TG-TRA160006      |
      | user111             | TG-TRA160006      |
    And we should have the following events
      | entity_id | name                                      | payload                                                                                                                                          | timestamp                |
      |           | allocation_source_created_or_renewed      | {"allocation_source_name": "TG-ENG150061", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": 1000000} | 2017-02-15 05:00:00+0000 |
      |           | allocation_source_compute_allowed_changed | {"allocation_source_name": "TG-ENG150061", "start_date": "2016-01-01T06:00:00Z", "end_date": "2017-06-30T05:00:00Z", "compute_allowed": 1000000} | 2017-02-15 05:00:00+0000 |
      | user108   | user_allocation_source_created            | {"allocation_source_name": "TG-ENG150061"}                                                                                                       | 2017-02-15 05:00:00+0000 |
      | user109   | user_allocation_source_created            | {"allocation_source_name": "TG-ENG150061"}                                                                                                       | 2017-02-15 05:00:00+0000 |
      |           | allocation_source_created_or_renewed      | {"allocation_source_name": "TG-TRA160006", "start_date": "2017-01-22T06:00:00Z", "end_date": "2018-01-21T06:00:00Z", "compute_allowed": 600000}  | 2017-02-15 05:00:00+0000 |
      |           | allocation_source_compute_allowed_changed | {"allocation_source_name": "TG-TRA160006", "start_date": "2017-01-22T06:00:00Z", "end_date": "2018-01-21T06:00:00Z", "compute_allowed": 600000}  | 2017-02-15 05:00:00+0000 |
      | user109   | user_allocation_source_created            | {"allocation_source_name": "TG-TRA160006"}                                                                                                       | 2017-02-15 05:00:00+0000 |
      | user111   | user_allocation_source_created            | {"allocation_source_name": "TG-TRA160006"}                                                                                                       | 2017-02-15 05:00:00+0000 |

  @skip
  Scenario: Generate reports