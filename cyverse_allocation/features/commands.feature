# TEST Commands for
#    Allocation Source Creation                AND
#    Allocation Source Renewal Strategy Change AND
#    Allocation Source Name Change             AND
#    Allocation Source Compute Allowed Change


Feature: Commands Testing

  Background:
      Given a user

  ######################################################################################################

  Scenario Outline: Allocation Source Creation

      When create_allocation_source command is fired
      |  name   |  compute allowed   |  renewal strategy    |
      |  <name> |  <compute_allowed> |  <renewal_strategy>  |

      Then allocation source is created = <allocation_source_is_created>

  Examples: Payloads
      |  name                     |  compute_allowed   |  renewal_strategy   |  allocation_source_is_created  |
      |  DefaultAllocationSource  |  250               |  default            |  True                          |
      |  DefaultAllocationSource  |  -100              |  default            |  False                         |

  ######################################################################################################

  Scenario Outline: Change Renewal Strategy
      Given An Allocation Source with renewal strategy
      |  renewal strategy       |
      |  <old_renewal_strategy> |

      When  change_renewal_strategy command is fired with <new_renewal_strategy>
      Then  renewal strategy is changed = <renewal_strategy_is_changed>

  Examples: Renewal Strategies
      |  old_renewal_strategy   |  new_renewal_strategy  | renewal_strategy_is_changed  |
      |  default                |  workshop              | True                         |
      |  biweekly               |  biyearly              | False                        |

#  ######################################################################################################
#
  Scenario Outline: Change Allocation Source Name
      Given An Allocation Source with name
      |  name       |
      |  <old_name> |
      When  change_allocation_source_name command is fired with <new_name>
      Then  name is changed = <name_is_changed>

  Examples: Names
      |  old_name                |  new_name                  |  name_is_changed  |
      |  DefaultAllocationSource |  WorkshopAllocationSource  |  True             |
#
#  ######################################################################################################

  Scenario Outline: Change Compute Allowed
      Given Allocation Source with compute allowed and compute used
      | compute_allowed       | compute_used   |
      | <old_compute_allowed> | <compute_used> |

      When  change_compute_allowed command is fired with <new_compute_allowed>
      Then  compute allowed is changed = <compute_allowed_is_changed>

  Examples: Compute Allowed Values
      |  old_compute_allowed    |  new_compute_allowed  | compute_used  | compute_allowed_is_changed |
      |  128                    |  240                  |  0            | True                       |
      |  240                    |  72                   |  150          | False                      |
      |  240                    |  72                   |   50          | True                       |

#  ######################################################################################################

  Scenario Outline: Remove Allocation Source
       Given Allocation Source
        |  name   |  compute allowed   |  renewal strategy    |
        |  <name> |  <compute_allowed> |  <renewal_strategy>  |

       When Allocation Source is removed
       Then Allocation Source Removal = <allocation_source_is_removed>

  Examples: Remove Allocation Source
        |  name                      |  compute_allowed   |  renewal_strategy   |  allocation_source_is_removed  |
        |  DefaultAllocationSource   |  250               |  default            |  True                          |
        |  NewAllocationSource       |  100               |  default            |  True                          |

#  ######################################################################################################

  Scenario Outline: Assign User to Allocation Source
       Given Allocation Source
        |  name   |  compute allowed   |  renewal strategy    |
        |  <name> |  <compute_allowed> |  <renewal_strategy>  |

       When User is assigned to the allocation source
       Then User assignment = <user_is_assigned>

  Examples: User Allocation Source
        |  name                      |  compute_allowed   |  renewal_strategy   |  user_is_assigned  |
        |  DefaultAllocationSource   |  250               |  default            |  True              |
        |  NewAllocationSource       |  100               |  default            |  True              |

#  ######################################################################################################

  Scenario Outline: Remove User from Allocation Source
     Given User assigned to Allocation Source
      |  name   |  compute allowed   |  renewal strategy    |
      |  <name> |  <compute_allowed> |  <renewal_strategy>  |

     When User is removed from Allocation Source
     Then User removal = <user_is_removed>

  Examples: User Allocation Source
        |  name                      |  compute_allowed   |  renewal_strategy   |  user_is_removed  |
        |  DefaultAllocationSource   |  250               |  default            |  True              |
        |  NewAllocationSource       |  100               |  default            |  True              |
