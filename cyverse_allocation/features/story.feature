# Story testing
#
#
#


Feature: Testing a story

  Background:
    Given one admin user and two regular users who can launch instances


  Scenario: Use cases of allocation source

    When admin creates allocation source
    |  name                       |  compute allowed   |  renewal strategy   |   allocation_source_id | date_created            |
    |  DefaultAllocationSource    |  250               |  default            |   1                    | current                 |

    And Users are added to allocation source
    |  username  | allocation_source_id    |
    |  amitj     |   1                     |

    And User launch Instance
    | username  | cpu | instance_id  | start_date |
    | amitj     |  1  |     1        |   current  |

    And User adds instance to allocation source
    | username    | instance_id  | allocation_source_id |
    |  amitj      | 1            | 1                    |

    And User instance runs for some days
    | username   | instance_id  | days  | status       |
    | amitj      |      1       |   2   | active       |


    Then calculate allocations used by allocation source after certain number of days
    |  report start date                  | number of days   | compute used      | compute remaining    | allocation_source_id |
    |      current                        |  4               |     48            |      452             | 1                    |

