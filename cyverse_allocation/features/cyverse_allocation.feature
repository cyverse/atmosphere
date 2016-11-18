Feature: Sample test with scenario builder

  Scenario: create a user (Amit), create an allocation source TestAllocationSource and assign it to Amit

    Given we create a new user, Amit
    when we create and assign an allocation source TestAllocationSource with default renewal to Amit
    then Amit should have the allocation source TestAllocationSource


  Scenario: Amit creates an instance and runs it for two hours.
  Verify the total usage of TestAllocationSource is 0 because
  instance is not assigned to it

    Given Amit creates an instance
    when Amits instance runs for 2 hours
    then the total usage on TestAllocationSource is 0 hours


  Scenario: Amit assigns instance to TestAllocationSource and the instance runs for another 2 hours.
  Verify total usage on TestAllocationSource is 2 hours

    Given Amit assigns instance to TestAllocationSource
    when Amits instance runs for another 2 hours
    then the total usage on TestAllocationSource is 2 hours


  Scenario: Create another user (Julian) and assign TestAllocationSource to
  Julian 1 hour after assigning it to Amit. Julian launches an instance
  on TestAllocationSource and runs it for 3 hours
  Verify TestAllocationSource usage is

    Given we create user, Julian and assign him to TestAllocationSource 1 hour after Amit is assigned
    when Julian launches an instance on TestAllocationSource and runs it for 3 hours
    then the total usage on TestAllocationSource source is 5 hours


  Scenario: Create an allocation source, DefaultAllocationSource and verify if
  allocation_source_created event is fired and the renewal_strategy is default

    Given default settings
    when new allocation source DefaultAllocationSource is created with compute allowed 128
    then allocation_source_created event is fired for DefaultAllocationSource
    and renewal_strategy for allocation source is default


  Scenario: Assign Amit to DefaultAllocationSource. Amit runs an instance on DefaultAllocationSource
  for 1 month. Verify renewal event is fired for DefaultAllocationSource.
  Compare the compute_used on 29th day and 30th day for DefaultAllocationSource

    Given Amit is assigned to DefaultAllocationSource
    when Amit runs an instance on DefaultAllocationSource for 3 days
    then renewal event is fired after 1 month for DefaultAllocationSource
    and compute_allowed on the 30th day is 184 after the carry over

