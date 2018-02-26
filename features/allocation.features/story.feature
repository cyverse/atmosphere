# Story testing
#
#
#


Feature: Testing a story

  Background:
    Given one admin user and two regular users who can launch instances


  Scenario: Use cases of allocation source

    Given a current time of "February 21, 2018 10:44:22 UTC"

    When admin creates allocation source
    |  name                       |  compute allowed   |  renewal strategy   |   allocation_source_id | date_created |
    |  DefaultAllocationSource    |  250               |  default            |   1                    | current      |

    And Users are added to allocation source
    |  username    | allocation_source_id    |
    |  amitj       |   1                     |
    |  julianp     |   1                     |

    And User launch Instance
    | username    | cpu | instance_id  | start_date |
    | amitj       |  1  |     1        |   current  |
    | julianp     |  2  |     2        |   current  |

    And User adds instance to allocation source
    | username      | instance_id  | allocation_source_id |
    |  amitj        | 1            | 1                    |
    |  julianp      | 2            | 1                    |

    And User instance runs for some days
    | username     | instance_id  | days  | status       |
    | amitj        |      1       |   2   | active       |
    | julianp      |      2       |   4   | active       |

    ## NOTE: Currently, the rules engine is set to renew in every 3 days. After every renewal the compute used is reset and remaining compute is carried over

    Then calculate allocations used by allocation source after certain number of days
    |  report start date                  | number of days   | total compute used   | current compute used | current compute allowed | allocation_source_id |
    |      current                        |  4               |     240              | 240                  | 250                     | 1                    |

