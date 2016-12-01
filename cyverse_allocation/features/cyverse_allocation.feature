Feature: Sample test with scenario builder

  Scenario: create a user (Amit), create an allocation source TestAllocationSource and assign it to Amit

    Given we create a new user, Amit
    When we create and assign an allocation source TestAllocationSource with default renewal to Amit
    Then Amit should have the allocation source TestAllocationSource


  Scenario: Amit creates an instance and runs it for two hours.
  Verify the total usage of TestAllocationSource is 0 because
  instance is not assigned to it

    Given Amit creates an instance
    When Amits instance runs for 2 hours
    Then the total usage on TestAllocationSource is 0 hours


  Scenario: Amit assigns instance to TestAllocationSource and the instance runs for another 2 hours.
  Verify total usage on TestAllocationSource is 2 hours

    Given Amit assigns instance to TestAllocationSource
    When Amits instance runs for another 2 hours
    Then the total usage on TestAllocationSource is 2 hours


  Scenario: Create another user (Julian) and assign TestAllocationSource to
  Julian 1 hour after assigning it to Amit. Julian launches an instance
  on TestAllocationSource and runs it for 3 hours
  Verify TestAllocationSource usage is

    Given we create user, Julian and assign him to TestAllocationSource 1 hour after Amit is assigned
    When Julian launches an instance on TestAllocationSource and runs it for 3 hours
    Then the total usage on TestAllocationSource source is 5 hours


  Scenario: Create an allocation source, DefaultAllocationSource and verify if
  allocation_source_created event is fired and the renewal_strategy is default

    Given default settings
    When new allocation source DefaultAllocationSource is created with compute allowed 128
    Then allocation_source_created event is fired for DefaultAllocationSource
    And renewal_strategy for allocation source is default


  Scenario: Assign Amit to DefaultAllocationSource. Amit runs an instance on DefaultAllocationSource
  for 1 month. Verify renewal event is fired for DefaultAllocationSource.
  Compare the compute_used on 29th day and 30th day for DefaultAllocationSource

    Given Amit is assigned to DefaultAllocationSource
    When Amit runs an instance on DefaultAllocationSource for 3 days
    Then renewal event is fired after 1 month for DefaultAllocationSource
    And compute_allowed on the 30th day is 184 after the carry over

  Scenario: DefaultAllocationSource changes its renewal strategy to bi-weekly after a month.
  Amit continues running instance on DefaultAllocationSource for another month. Assign Julian to the allocation source.
  Julian runs an instance on the allocation source for three weeks before suspending.
  Verify two renewal events are fired and the allocation source compute allowed and compute used are as expected


    Given DefaultAllocationSource changes its renewal strategy to bi-weekly and Julian is assigned to DefaultAllocationSource
    When Amit runs an instance for 5 days before the first renewal and Julian launches a new instance and runs it for 4 days before the first renewal and 8 days before the second renewal on the DefaultAllocationSource
    Then renewal event is fired twice twice after every two weeks
