# Story testing
#
#
#


Feature: Testing a story

  Background:
    Given one admin user and two regular users who can launch instances


  Scenario Outline: Use cases of allocation source

    When admin creates allocation source
    |  name   |  compute allowed   |  renewal strategy    |
    |  <name> |  <compute_allowed> |  <renewal_strategy>  |

    And Users are added to allocation source
    |  username  | allocation source name    |
    |  amitj     |   DefaultAllocationSource |
    |  julianp   |   DefaultAllocationSource |

    And User launch Instance
    | username  | cpu | instance_id  | start_date               |
    | amitj     |  1  |     1        |   current                |
    | amitj     |  3  |     2        |  2016-10-03T00:00+00:00  |
    | julianp   |  4  |     3        |   current                |

    And User instance runs for some days
    | username   | instance_id  | days  | status       |
    | amitj      |      2       |   5   | active       |
    | julianp    |      3       |   8   | deploy_error |
    | amitj      |      1       |   2   | active       |

    Then after days = <no_of_days> Allocation source used = <compute_used> and remaining compute = <compute_remaining>

  Examples: Story Testing
    |  name                       |  compute_allowed   |  renewal_strategy   | no_of_days | compute_used | compute_remaining |
    |  DefaultAllocationSource    |  250               |  default            |      4     |     72       |      428          |
    |  DefaultAllocationSource2   |  250               |  default            |      2     |     72       |      178          |