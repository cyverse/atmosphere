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

    And Users added to allocation source launch instance (at the same time)
    | user_id | cpu  |  days_instance_is_active  |
    |  1      |  1   |     2                     |
    |  2      |  1   |     1                     |

    Then after days = <no_of_days> Allocation source used = <compute_used> and remaining compute = <compute_remaining>

  Examples: Story Testing
    |  name                       |  compute_allowed   |  renewal_strategy   | no_of_days | compute_used | compute_remaining |
    |  DefaultAllocationSource    |  250               |  default            |      4     |     72       |      428          |
    |  DefaultAllocationSource2   |  250               |  default            |      2     |     72       |      178          |