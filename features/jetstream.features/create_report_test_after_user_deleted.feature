@skip-if-cyverse
Feature: Testing create_report task after user deleted from allocation source

  @skip-if-cyverse
  Scenario Outline: testing create_reports task

    Given a test Allocation Source

    When Allocation Source is assigned to Users
      | number of users assigned to allocation source |
      | <number_of_users_assigned>                    |

    And All Users run an instance on Allocation Source for indefinite duration
      | cpu size of instance |
      | <cpu_size>           |

    And create_reports task is run for the first time
      | task runs every x minutes    |
      | <task_interval_time_minutes> |

    And Users are deleted from Allocation Source after first create_reports run
      | number of users deleted from allocation source | users deleted x minutes after the first create_reports run |
      | <number_of_users_deleted>                      | <minutes_used_by_deleted_user>                             |

    Then Total expected allocation usage for allocation source matches calculated allocation usage from reports after next create_reports run
      | total expected allocation usage in minutes |
      | <total_allocation_usage_minutes>           |

    Examples: create_report accuracy test

      | number_of_users_assigned | cpu_size | task_interval_time_minutes | number_of_users_deleted | minutes_used_by_deleted_user | total_allocation_usage_minutes |
      | 10                       | 1        | 15                         | 1                       | 10                           | 295                            |
      | 5                        | 4        | 15                         | 4                       | 5                            | 440                            |