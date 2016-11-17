Feature: Sample test with scenario builder

  Scenario: create a user and check his allocation source
    Given we create a new user
    when we create and assign an allocation source to user
    then user should have an allocation source
