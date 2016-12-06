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
      Given <name> <compute allowed> <renewal strategy>
      When  create_allocation_source command is fired
      Then  <allocation source is created>

  Examples: Payloads
      |  name                     |  compute allowed  |  renewal strategy  |  allocation source is created  |
      |  DefaultAllocationSource  |  250              |  default           |  True                          |

  ######################################################################################################

  Scenario Outline: Change Renewal Strategy
      Given An Allocation Source
      When  change_renewal_strategy command is fired
      Then  <old renewal strategy> is changed to <new renewal strategy>

  Examples: Renewal Strategies
      |  old renewal strategy  |  new renewal strategy  |
      |  default               |  workshop              |

  ######################################################################################################

  Scenario Outline: Change Allocation Source Name
      Given An Allocation Source
      When  change_allocation_source_name command is fired
      Then  <old name> is changed to <new name>

  Examples: Names
      |  old name                |  new name                  |
      |  DefaultAllocationSource |  WorkshopAllocationSource  |

  ######################################################################################################

  Scenario Outline: Change Compute Allowed
      Given An Allocation Source
      When  change_compute_allowed command is fired
      Then  <old compute allowed> is changed to <new compute allowed>

  Examples: Compute Allowed Values
      |  old compute allowed    |  new compute allowed  |
      |  128                    |  240                  |
      |  240                    |  72                   |

  ######################################################################################################