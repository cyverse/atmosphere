Feature: Should be able to use Jetstream, even when Atmosphere can't reach TAS API
  As long as:
  - They have logged in before
  - They were valid the last time we were able to check with the TAS API
  Note: New Jetstream users who have never logged into Atmosphere will be disabled until we can check the TAS API

  Scenario Outline: Log in and check whether the user is valid or not
    Given a dummy browser
    And a TAS API driver
    And a current time of '2017-02-15T05:00:00Z'
    And we clear the local cache
    And we set up the TAS API failover scenario example
      | index   | user   | is_tas_up   | has_tas_account   | has_valid_allocation   | has_local_allocation   | user_is_valid   |
      | <index> | <user> | <is_tas_up> | <has_tas_account> | <has_valid_allocation> | <has_local_allocation> | <user_is_valid> |

    When we get all projects
    And we fill user allocation sources from TAS

    Given "<user>" as the persona
    When I set "username" to "<user>"
    And I set "password" to "some-very-long-string"

    When I try to log in with valid XSEDE project required
    Then the login attempt should succeed

    When we ensure local allocation is created or deleted

    Then the user should be valid - <user_is_valid>
    Examples:
      | index | user    | is_tas_up | has_tas_account | has_valid_allocation | has_local_allocation | user_is_valid |
      | 0     | user300 | No        | No              | No                   | No                   | No            |
      | 1     | user301 | No        | No              | No                   | Yes                  | Yes           |
      | 2     | user302 | No        | No              | Yes                  | Yes                  | Yes           |
      | 3     | user303 | No        | No              | Yes                  | No                   | No            |
      | 4     | user304 | No        | Yes             | Yes                  | No                   | No            |
      | 5     | user305 | No        | Yes             | Yes                  | Yes                  | Yes           |
      | 6     | user306 | No        | Yes             | No                   | Yes                  | Yes           |
      | 7     | user307 | No        | Yes             | No                   | No                   | No            |
      | 8     | user308 | Yes       | Yes             | No                   | No                   | No            |
      | 9     | user309 | Yes       | Yes             | No                   | Yes                  | No            |
      | 10    | user310 | Yes       | Yes             | Yes                  | Yes                  | Yes           |
      | 11    | user311 | Yes       | Yes             | Yes                  | No                   | Yes           |
      | 12    | user312 | Yes       | No              | Yes                  | No                   | No            |
      | 13    | user313 | Yes       | No              | Yes                  | Yes                  | No            |
      | 14    | user314 | Yes       | No              | No                   | Yes                  | No            |
      | 15    | user315 | Yes       | No              | No                   | No                   | No            |