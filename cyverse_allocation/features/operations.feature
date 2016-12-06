# TEST Operations for
#    Allocation Source Assignment to User  AND
#    Total Usage Calculation               AND
#    Renewal Strategy Check                AND
#    Carry Overs                           AND
#    Instance Suspension


Feature: Operation Testing

  Background:
      Given a user and an allocation source

  ######################################################################################################

  Scenario: Allocation Source assignment
      Given the background
      When  allocation source is assigned to user
      Then  user can run an instance on the allocation source

  ######################################################################################################

  Scenario: Total Usage calculation
      Given user assigned to allocation source
      When  user runs instance with <cpu> for <time (hours)>
      Then  <total usage (hours)> allocations are used

  Examples: Usage
      |  cpu  |  time (hours)    |  total usage (hours)  |
      |   1   |  2               |  2                    |
      |   4   |  5               |  20                   |

  ######################################################################################################

  Scenario: Renewal Strategy Check
      Given allocation source with <renewal strategy>
      When  <days since last renewed> have passed
      Then  <number of renewal events> are fired

  Examples: Renewal Strategy
      |  renewal strategy  |  days since last renewed    |  number of renewal events  |
      |   default          |  30                         |  1                         |
      |   default          |  100                        |  3                         |
      |   workshop         |  20                         |  0                         |

  ######################################################################################################

  Scenario: Carry Over verification
      Given allocation source with <renewal strategy> and <compute allowed>
      When  <days since last renewed> have passed
      And   <total usage> allocations are used
      Then  on the next renewal date <new compute allowed> is used

  Examples: Renewal Strategy
      |  renewal strategy  |  compute allowed    |  days since last renewed  | total usage | new compute allowed |
      |   default          |  128                |  29                       | 72          | 184                 |

  ######################################################################################################

  Scenario: Instance Suspension
      Given allocation source with <compute allowed>
      When  user uses <total usage> allocations
      Then  <instance is suspended>

  Examples: Renewal Strategy
      |  compute allowed  |  total usage    |  instance is suspended   |
      |   300             |  299            |  False                   |
      |   128             |  130            |  True                    |

  ######################################################################################################