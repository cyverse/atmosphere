@skip-if-jetstream
Feature: Launching & editing of an instance

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


  Scenario: Launch instance and assign allocation source
    Given "user407" as the persona
    When I set "username" to "user407"
    And I set "password" to "some-very-long-string"
    And we create a new user
    Given a current time of '2017-02-16T06:00:00Z' with tick = False
    When I log in
    And we create an identity for the current persona on provider "MockProvider"
    And we ensure that the user has an allocation source
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
      | user407             | user407           |
    When we update CyVerse snapshots
    Then we should have the following allocation source snapshots
      | name    | compute_used | compute_allowed |
      | user407 | 0            | 168             |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user407             | user407           | 0.000        | 0.000     |
    When I get my allocation sources from the API I should see
      | name    | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | user407 | 168             | 2017-02-16 06:00:00+0000 | None     | 0.000        | 0.000            | 2017-02-16 06:00:00+0000 | default          | 0.000             | 0.000          | 2017-02-16 06:00:00+0000 |
    Given a current time of '2017-02-16T07:00:00Z' with tick = False
    When we create a provider machine for current persona
    And we create an active instance
    And we get the details for the active instance via the API
    Then the API response code is 200
    And the API response contains
    """
    {
      "usage": -1,
      "start_date": "2017-02-16T07:00:00Z",
      "status": "active",
      "shell": false,
      "vnc": false,
      "end_date": null,
      "scripts": [],
      "ip_address": null,
      "project": null,
      "name": "Instance in active",
      "allocation_source": null,
      "activity": ""
    }
    """
    # Assign the allocation source to the instance
    Given a current time of '2017-02-16T07:01:00Z' with tick = False
    When I assign allocation source "user407" to active instance
    Then the API response code is 201
    When we get the details for the active instance via the API
    Then the API response code is 200
    And the API response contains
    """
    {
      "usage": 0.0,
      "start_date": "2017-02-16T07:00:00Z",
      "status": "active",
      "shell": false,
      "vnc": false,
      "end_date": null,
      "scripts": [],
      "ip_address": null,
      "project": null,
      "name": "Instance in active",
      "activity": ""
    }
    """
    And I set "response_data" to attribute "data" of "response"
    And I set "allocation_source" to key "allocation_source" of "response_data"
    Then "allocation_source" contains
    """
    {
      "name": "user407",
      "renewal_strategy": "default",
      "compute_allowed": 168,
      "start_date": "2017-02-16T06:00:00Z"
    }
    """
    And I set "instance01" to another variable "active_instance"
    # Check usage immediately after launching instance
    Given a current time of '2017-02-16T07:02:00Z' with tick = False
    When we update CyVerse snapshots
    Then we should have the following allocation source snapshots
      | name    | compute_used | compute_allowed |
      | user407 | 0.020        | 168             |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user407             | user407           | 0.020        | 1.000     |
    When I get my allocation sources from the API I should see
      | name    | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | user407 | 168             | 2017-02-16 06:00:00+0000 | None     | 0.020        | 1.000            | 2017-02-16 07:02:00+0000 | default          | 0.020             | 1.000          | 2017-02-16 07:02:00+0000 |
    # Check usage after an hour
    Given a current time of '2017-02-16T08:00:00Z' with tick = False
    When we update CyVerse snapshots
    Then we should have the following allocation source snapshots
      | name    | compute_used | compute_allowed |
      | user407 | 0.980        | 168             |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user407             | user407           | 0.980        | 1.000     |

    When I get my allocation sources from the API I should see
      | name    | compute_allowed | start_date               | end_date | compute_used | global_burn_rate | updated                  | renewal_strategy | user_compute_used | user_burn_rate | user_snapshot_updated    |
      | user407 | 168             | 2017-02-16 06:00:00+0000 | None     | 0.980        | 1.000            | 2017-02-16 08:00:00+0000 | default          | 0.980             | 1.000          | 2017-02-16 08:00:00+0000 |


  Scenario: Launch instance and edit name
    Given "user408" as the persona
    When I set "username" to "user408"
    And I set "password" to "some-very-long-string"
    And we create a new user
    Given a current time of '2017-02-16T06:00:00Z' with tick = False
    When I log in
    And we create an identity for the current persona on provider "MockProvider"
    And we ensure that the user has an allocation source
    Given a current time of '2017-02-16T07:00:00Z' with tick = False
    When we create a provider machine for current persona
    And we create an active instance
    And we get the details for the active instance via the API
    Then the API response code is 200
    And the API response contains
    """
    {
      "usage": -1,
      "start_date": "2017-02-16T07:00:00Z",
      "status": "active",
      "shell": false,
      "vnc": false,
      "end_date": null,
      "scripts": [],
      "ip_address": null,
      "project": null,
      "name": "Instance in active",
      "allocation_source": null,
      "activity": ""
    }
    """
    When I change the name of the active instance to "My New Instance Name"
    # TODO: Should really be 201...
    Then the API response code is 200
    And the API response contains
    """
    {
      "usage": -1,
      "start_date": "2017-02-16T07:00:00Z",
      "status": "active",
      "shell": false,
      "vnc": false,
      "end_date": null,
      "scripts": [],
      "ip_address": null,
      "project": null,
      "name": "My New Instance Name",
      "activity": ""
    }
    """
    When we get the details for the active instance via the API
    Then the API response code is 200
    And the API response contains
    """
    {
      "usage": -1,
      "start_date": "2017-02-16T07:00:00Z",
      "status": "active",
      "shell": false,
      "vnc": false,
      "end_date": null,
      "scripts": [],
      "ip_address": null,
      "project": null,
      "name": "My New Instance Name",
      "activity": ""
    }
    """
