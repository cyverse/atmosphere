Feature: Fractional burn rates

  Background:
#    Given one admin user and two regular users who can launch instances
    Given a dummy browser
    And "Admin" as the persona
    When I set "username" to "admin"
    And I set "password" to "very-clever-admin-password"
    And we create a new admin user

  @skip-if-jetstream
  Scenario: Default 1.0 burn rate for active instances
  'default': 0.0
  'active': 1.0
  'suspended': 0.0
  'shutoff': 0.0
  'shelved': 0.0
  'shelved_offloaded': 0.0

    Given a current time of "February 21, 2018 10:44:22 UTC"
    And a user "andrew"
    And a user "bettina"
    And a user "charles"
    And a user "daniella"
    And a user "eric"

    Given "Admin" as the persona
    When admin creates allocation source
      | name     | compute allowed | renewal strategy | allocation_source_id | date_created |
      | TG-00001 | 1000            | default          | 1                    | current      |
      | TG-00002 | 1000            | default          | 2                    | current      |
      | TG-00003 | 1000            | default          | 3                    | current      |
      | TG-00004 | 1000            | default          | 4                    | current      |
      | TG-00005 | 1000            | default          | 5                    | current      |

    And Users are added to allocation source
      | username | allocation_source_id |
      | andrew   | 1                    |
      | bettina  | 2                    |
      | charles  | 3                    |
      | daniella | 4                    |
      | eric     | 5                    |

    And User launch Instance
      | username | cpu | instance_id | start_date | initial_state     |
      | andrew   | 1   | 1           | current    | active            |
      | bettina  | 1   | 2           | current    | suspended         |
      | charles  | 1   | 3           | current    | shutoff           |
      | daniella | 1   | 4           | current    | shelved           |
      | eric     | 1   | 5           | current    | shelved_offloaded |

    And User adds instance to allocation source
      | username | instance_id | allocation_source_id |
      | andrew   | 1           | 1                    |
      | bettina  | 2           | 2                    |
      | charles  | 3           | 3                    |
      | daniella | 4           | 4                    |
      | eric     | 5           | 5                    |

    Given a current time of "February 22, 2018 10:44:22 UTC"

    Then calculate allocations used by allocation source after certain number of days
      | allocation_source_id | report start date | number of days | total compute used | current compute allowed |
      | 1                    | current           | 1              | 24                 | 1000                    |
      | 2                    | current           | 1              | 0                  | 1000                    |
      | 3                    | current           | 1              | 0                  | 1000                    |
      | 4                    | current           | 1              | 0                  | 1000                    |
      | 5                    | current           | 1              | 0                  | 1000                    |


  @skip-if-cyverse
  Scenario: Fractional burn rates for different instance states, before the new rates
  'active': 1.0

    Given a current time of "February 21, 2018 10:44:22 UTC"
    And a user "andrew"
    And a user "bettina"
    And a user "charles"
    And a user "daniella"
    And a user "eric"

    Given "Admin" as the persona
    When admin creates allocation source
      | name     | compute allowed | renewal strategy | allocation_source_id | date_created |
      | TG-00001 | 1000            | default          | 1                    | current      |
      | TG-00002 | 1000            | default          | 2                    | current      |
      | TG-00003 | 1000            | default          | 3                    | current      |
      | TG-00004 | 1000            | default          | 4                    | current      |
      | TG-00005 | 1000            | default          | 5                    | current      |

    And Users are added to allocation source
      | username | allocation_source_id |
      | andrew   | 1                    |
      | bettina  | 2                    |
      | charles  | 3                    |
      | daniella | 4                    |
      | eric     | 5                    |

    And User launch Instance
      | username | cpu | instance_id | start_date | initial_state     |
      | andrew   | 1   | 1           | current    | active            |
      | bettina  | 1   | 2           | current    | suspended         |
      | charles  | 1   | 3           | current    | shutoff           |
      | daniella | 1   | 4           | current    | shelved           |
      | eric     | 1   | 5           | current    | shelved_offloaded |

    And User adds instance to allocation source
      | username | instance_id | allocation_source_id |
      | andrew   | 1           | 1                    |
      | bettina  | 2           | 2                    |
      | charles  | 3           | 3                    |
      | daniella | 4           | 4                    |
      | eric     | 5           | 5                    |

    Given a current time of "February 22, 2018 10:44:22 UTC"

    Then calculate allocations used by allocation source after certain number of days
      | allocation_source_id | report start date | number of days | total compute used | current compute allowed |
      | 1                    | current           | 1              | 24                 | 1000                    |
      | 2                    | current           | 1              | 0                  | 1000                    |
      | 3                    | current           | 1              | 0                  | 1000                    |
      | 4                    | current           | 1              | 0                  | 1000                    |
      | 5                    | current           | 1              | 0                  | 1000                    |


  @skip-if-cyverse
  Scenario: Fractional burn rates, with transition from old rates
  Rates at beginning:
  'active': 1.0
  Rates at the end:
  'active': 1.0
  'suspended': 0.75
  'shutoff': 0.5
  'shelved': 0.0
  'shelved_offloaded': 0.0

    Given a current time of "2018-11-11T00:00:00Z" with tick = False
    And a user "andrew"
    And a user "bettina"
    And a user "charles"
    And a user "daniella"
    And a user "eric"

    Given "Admin" as the persona
    When admin creates allocation source
      | name     | compute allowed | renewal strategy | allocation_source_id | date_created |
      | TG-00001 | 1000            | default          | 1                    | current      |
      | TG-00002 | 1000            | default          | 2                    | current      |
      | TG-00003 | 1000            | default          | 3                    | current      |
      | TG-00004 | 1000            | default          | 4                    | current      |
      | TG-00005 | 1000            | default          | 5                    | current      |

    And Users are added to allocation source
      | username | allocation_source_id |
      | andrew   | 1                    |
      | bettina  | 2                    |
      | charles  | 3                    |
      | daniella | 4                    |
      | eric     | 5                    |

    And User launch Instance
      | username | cpu | instance_id | start_date | initial_state     |
      | andrew   | 1   | 1           | current    | active            |
      | bettina  | 1   | 2           | current    | suspended         |
      | charles  | 1   | 3           | current    | shutoff           |
      | daniella | 1   | 4           | current    | shelved           |
      | eric     | 1   | 5           | current    | shelved_offloaded |

    And User adds instance to allocation source
      | username | instance_id | allocation_source_id |
      | andrew   | 1           | 1                    |
      | bettina  | 2           | 2                    |
      | charles  | 3           | 3                    |
      | daniella | 4           | 4                    |
      | eric     | 5           | 5                    |

    Given a current time of "2018-11-11T12:00:00Z" with tick = False
    Then calculate allocations used by allocation source after certain number of days
      | allocation_source_id | report start date | number of days | total compute used | current compute allowed |
      | 1                    | current           | 0.5            | 12                 | 1000                    |
      | 2                    | current           | 0.5            | 0                  | 1000                    |
      | 3                    | current           | 0.5            | 0                  | 1000                    |
      | 4                    | current           | 0.5            | 0                  | 1000                    |
      | 5                    | current           | 0.5            | 0                  | 1000                    |

    Given a current time of "2018-11-12T00:00:00Z" with tick = False
    Then calculate allocations used by allocation source after certain number of days
      | allocation_source_id | report start date | number of days | total compute used | current compute allowed |
      | 1                    | current           | 1              | 24                 | 1000                    |
      | 2                    | current           | 1              | 0                  | 1000                    |
      | 3                    | current           | 1              | 0                  | 1000                    |
      | 4                    | current           | 1              | 0                  | 1000                    |
      | 5                    | current           | 1              | 0                  | 1000                    |

    Given a current time of "2018-11-12T12:00:00Z" with tick = False
    Then calculate allocations used by allocation source after certain number of days
      | allocation_source_id | report start date | number of days | total compute used | current compute allowed |
      | 1                    | current           | 1.5            | 36                 | 1000                    |
      | 2                    | current           | 1.5            | 9                  | 1000                    |
      | 3                    | current           | 1.5            | 6                  | 1000                    |
      | 4                    | current           | 1.5            | 0                  | 1000                    |
      | 5                    | current           | 1.5            | 0                  | 1000                    |

    Given a current time of "2018-11-13T00:00:00Z" with tick = False
    Then calculate allocations used by allocation source after certain number of days
      | allocation_source_id | report start date | number of days | total compute used | current compute allowed |
      | 1                    | current           | 2              | 48                 | 1000                    |
      | 2                    | current           | 2              | 18                 | 1000                    |
      | 3                    | current           | 2              | 12                 | 1000                    |
      | 4                    | current           | 2              | 0                  | 1000                    |
      | 5                    | current           | 2              | 0                  | 1000                    |


  @skip-if-cyverse
  Scenario: Fractional burn rates for different instance states, after the new rates
  'active': 1.0
  'suspended': 0.75
  'shutoff': 0.5
  'shelved': 0.0
  'shelved_offloaded': 0.0

    Given a current time of "2018-11-13T00:00:00Z"
    And a user "andrew"
    And a user "bettina"
    And a user "charles"
    And a user "daniella"
    And a user "eric"

    Given "Admin" as the persona
    When admin creates allocation source
      | name     | compute allowed | renewal strategy | allocation_source_id | date_created |
      | TG-00001 | 1000            | default          | 1                    | current      |
      | TG-00002 | 1000            | default          | 2                    | current      |
      | TG-00003 | 1000            | default          | 3                    | current      |
      | TG-00004 | 1000            | default          | 4                    | current      |
      | TG-00005 | 1000            | default          | 5                    | current      |

    And Users are added to allocation source
      | username | allocation_source_id |
      | andrew   | 1                    |
      | bettina  | 2                    |
      | charles  | 3                    |
      | daniella | 4                    |
      | eric     | 5                    |

    And User launch Instance
      | username | cpu | instance_id | start_date | initial_state     |
      | andrew   | 1   | 1           | current    | active            |
      | bettina  | 1   | 2           | current    | suspended         |
      | charles  | 1   | 3           | current    | shutoff           |
      | daniella | 1   | 4           | current    | shelved           |
      | eric     | 1   | 5           | current    | shelved_offloaded |

    And User adds instance to allocation source
      | username | instance_id | allocation_source_id |
      | andrew   | 1           | 1                    |
      | bettina  | 2           | 2                    |
      | charles  | 3           | 3                    |
      | daniella | 4           | 4                    |
      | eric     | 5           | 5                    |

    Given a current time of "2018-11-14T00:00:00Z"

    Then calculate allocations used by allocation source after certain number of days
      | allocation_source_id | report start date | number of days | total compute used | current compute allowed |
      | 1                    | current           | 1              | 24                 | 1000                    |
      | 2                    | current           | 1              | 18                 | 1000                    |
      | 3                    | current           | 1              | 12                 | 1000                    |
      | 4                    | current           | 1              | 0                  | 1000                    |
      | 5                    | current           | 1              | 0                  | 1000                    |