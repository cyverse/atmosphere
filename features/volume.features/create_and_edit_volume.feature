@wip
Feature: Create volume and add to projects

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


  @skip-if-jetstream
  Scenario: Create project and volume, assign volume to project
    Given "user607" as the persona
    When I set "username" to "user607"
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
      | user607             | user607           |
    When we update CyVerse snapshots
    Then we should have the following allocation source snapshots
      | name    | compute_used |
      | user607 | 0            |
    And we should have the following user allocation source snapshots
      | atmosphere_username | allocation_source | compute_used | burn_rate |
      | user607             | user607           | 0.000        | 0.000     |
    When I get the projects via the API
    Then the API response code is 200
    And the API response contains
    """
    {
      "count": 0,
      "results": []
    }
    """
    When I get the volumes via the API
    Then the API response code is 200
    And the API response contains
    """
    []
    """

    When I create a project called "My First Project" via the API
    Then the API response code is 201
    And the API response contains
    """
    {
      "name": "My First Project",
      "description": "My First Project",
      "images": [],
      "instances": [],
      "volumes": [],
      "start_date": "2017-02-16T06:00:00Z",
      "end_date": null
    }
    """
    And I set "response_data" to attribute "data" of "response"
    And I set "project_id" to key "id" of "response_data"
    When I get the projects via the API
    Then the API response code is 200
    And the API response contains
    """
    {
      "count": 1,
      "results": [
        {
          "name": "My First Project",
          "description": "My First Project",
          "images": [],
          "instances": [],
          "volumes": [],
          "start_date": "2017-02-16T06:00:00Z",
          "end_date": null
        }
      ]
    }
    """
    Given a current time of '2017-02-16T07:00:00Z' with tick = False
    When I create a volume with name "volume_01" and size 1 using API
    Then the API response code is 201
    And the API response contains
    """
    {
      "name": "volume_01",
      "created_by": "user607",
      "size": 1,
      "description": null,
      "start_date": "2017-02-16 07:00:00+0000",
      "end_date": null,
      "attach_data": null,
      "mount_location": null,
      "identity": {
        "created_by": "user607"
      },
      "project": null,
      "status": "Unknown"
    }
    """
    And I set "response_data" to attribute "data" of "response"
    And I set "volume_id" to key "id" of "response_data"
    When I get the volumes via the API
    Then the API response code is 200
    And the API response contains
    """
    [
      {
        "name": "volume_01",
        "created_by": "user607",
        "size": 1,
        "description": null,
        "start_date": "2017-02-16 07:00:00+0000",
        "end_date": null,
        "attach_data": null,
        "mount_location": null,
        "identity": {
          "created_by": "user607"
        },
        "project": null,
        "status": "Unknown"
      }
    ]
    """
    When I associate volume "volume_id" with project "project_id" via the API
    Then the API response code is 201
    And the API response contains
    """
    {
      "project": {
        "id": %(project_id)s,
        "name": "My First Project",
        "description": "My First Project",
        "owner": "user607",
        "start_date": "2017-02-16T06:00:00Z",
        "end_date": null
      },
      "volume": {
        "name": "volume_01",
        "size": 1,
        "description": null,
        "start_date": "2017-02-16 07:00:00+0000",
        "end_date": null,
        "project": {
          "id": %(project_id)s,
          "name": "My First Project",
          "description": "My First Project",
          "owner": "user607",
          "start_date": "2017-02-16T06:00:00Z",
          "end_date": null
        },
        "user": {
          "username": "user607"
        }
      }
    }
    """
#    # I am not sure how project_volumes will be queried now. Try it out.
#    And I set "response_data" to attribute "data" of "response"
#    And I set "project_volume_id" to key "id" of "response_data"
#    When I get the project volumes via the API
#    Then the API response code is 200
#    And the API response contains
#    """
#    [
#      {
#        "project": {
#          "name": "My First Project",
#          "description": "My First Project",
#          "owner": "user607",
#          "start_date": "2017-02-16T06:00:00Z",
#          "end_date": null
#        },
#        "volume": {
#          "name": "volume_01",
#          "size": 1,
#          "description": null,
#          "start_date": "2017-02-16 07:00:00+0000",
#          "end_date": null,
#          "projects": [%(project_id)s],
#          "user": {
#            "username": "user607"
#          }
#        }
#      }
#    ]
#    """

    When I get the volumes via the API
    Then the API response code is 200
    # Figure out how to check the 'projects' list.
    And the API response contains
    """
    [
      {
        "name": "volume_01",
        "created_by": "user607",
        "size": 1,
        "description": null,
        "start_date": "2017-02-16 07:00:00+0000",
        "end_date": null,
        "attach_data": null,
        "mount_location": null,
        "identity": {
          "created_by": "user607"
        },
        "project": %(project_id)s,
        "status": "Unknown"
      }
    ]
    """