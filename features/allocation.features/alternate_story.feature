# Story testing
#
#
#


Feature: Testing an Alternate story

  Background:
    Given one admin user and two regular users who can launch instances


  Scenario: Reproducing the bug with allocation source logic

    When admin creates allocation source
    |  name     |  compute allowed   |  renewal strategy   |   allocation_source_id | date_created |
    |  amitj    |  168               |  default            |   1                    | current      |
    |  julianp  |  168               |  default            |   2                    | current      |

    And Users are added to allocation source
    |  username    | allocation_source_id    |
    |  amitj       |   1                     |
    |  julianp     |   2                     |

    And User launch Instance and no statushistory is created
    | username    | cpu | instance_id  | start_date |
    | amitj       |  1  |     1        |   current  |

    And Instance Allocation Source Changed Event is fired BEFORE statushistory is created
    | username      | instance_id  | allocation_source_id |
    |  amitj        | 1            | 1                    |

    And User launch Instance
    | username    | cpu | instance_id  | start_date |
    | julianp     |  1  |     2        |   current  |

    And User adds instance to allocation source
    | username      | instance_id  | allocation_source_id |
    |  julianp      | 2            | 2                    |

    And User instance runs for some days
    | username     | instance_id  | days  | status       |
    | amitj        |      1       |   1   | active       |
    | julainp      |      2       |   1   | active       |

    ## NOTE: Currently, the rules engine is set to renew in every 3 days. After every renewal the compute used is reset and remaining compute is carried over

    Then calculate allocations used by allocation source after certain number of days
    |  report start date                  | number of days   | total compute used   | current compute used | current compute allowed | allocation_source_id |
    |      current                        |  1               |     24               | 24                   | 168                     | 1                    |
    |      current                        |  1               |     24               | 24                   | 168                     | 2                    |

    And Compute Allowed is increased for Allocation Source
    | allocation_source_id | new_compute_allowed |
    |          1           |    400              |

    # test that one off renewal task does not reset EVERY allocation source to the original compute allowed value
    And One off Renewal task is run without rules engine
    | current compute used | current compute allowed | allocation_source_id |
    | 0                    | 400                     | 1                    |
    | 0                    | 168                     | 2                    |
