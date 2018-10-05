# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)

<!--
## [<exact release including patch>](<github compare url>) - <release date in YYYY-MM-DD>
### Added
  - <summary of new features>

### Changed
  - <for changes in existing functionality>

### Deprecated
  - <for soon-to-be removed features>

### Removed
  - <for now removed features>

### Fixed
  - <for any bug fixes>

### Security
  - <in case of vulnerabilities>
-->

## [Unreleased](https://github.com/cyverse/atmosphere/compare/v34-4...HEAD) - YYYY-MM-DD
### Added
  - Format codebase with `yapf` require code to be formatted in travis build
    ([#677](https://github.com/cyverse/atmosphere/pull/677))

### Changed
  - Refactored email to make variables and methods used for sending emails
    easier to understand and use
    ([#665](https://github.com/cyverse/atmosphere/pull/665))

### Fixed
  - Fix nginx gateway timeout on unshelve
    ([#686](https://github.com/cyverse/atmosphere/pull/686))

## [v34-4](https://github.com/cyverse/atmosphere/compare/v34-3...v34-4) - 2018-09-25
### Fixed
  - Fix un-registered service tasks
    ([#683](https://github.com/cyverse/atmosphere/pull/683))


## [v34-3](https://github.com/cyverse/atmosphere/compare/v34-2...v34-3) - 2018-09-24
### Changed
  - Upgrade to rtwo version 0.5.24 to get more defensive pagination logic
    ([#680](https://github.com/cyverse/atmosphere/pull/680))

## [v34-2](https://github.com/cyverse/atmosphere/compare/v34-1...v34-2) - 2018-09-21
### Fixed
  - Several issues in the TACC_API_TIMEOUT implementation prevented the
    desired behavior of offline (no access to tas) user validation
    ([#668](https://github.com/cyverse/atmosphere/pull/668))

## [v34-1](https://github.com/cyverse/atmosphere/compare/v34-0...v34-1) - 2018-09-18
### Fixed
  - Fix reference to deleted model ProviderDNSServerIP
    ([#673](https://github.com/cyverse/atmosphere/pull/673))
  - Upgrade to django-cyverse-auth 1.1.7 from 1.1.6 to avoid error in OAuth
    ([#674](https://github.com/cyverse/atmosphere/pull/674))

## [v34-0](https://github.com/cyverse/atmosphere/compare/v33-0...v34-0) - 2018-09-17
### Added
  - Added AccessTokens model, API view, and serializers to enable new feature
    on Troposphere that allows users to create personal access tokens that can
    be used to authenticate the user from things like Atmosphere CLI
    ([#648](https://github.com/cyverse/atmosphere/pull/648))
  - Add ability to configure allocation overrides
    ([#652](https://github.com/cyverse/atmosphere/pull/652))
  - Added api v2 delete support
    ([#654](https://github.com/cyverse/atmosphere/pull/654))
  - Introduce vulture to detect dead code
    ([#662](https://github.com/cyverse/atmosphere/pull/662))

### Changed
  - Updated Ansible version to 2.6.1 by changing requirements and changing
    `deploy.py` Playbook arg `--inventory-file` to `--inventory`
    ([#635](https://github.com/cyverse/atmosphere/pull/635))
  - Simplified v2 instance action api to exclude 'object' field
    ([#655](https://github.com/cyverse/atmosphere/pull/655))
  - Prefer importing settings from django.conf
    ([#658](https://github.com/cyverse/atmosphere/pull/658))
  - Added timeout of 5 sec to tas api for user validation, and refactored to
    make validation more explicit in the absence of the old selected_identity
    notion ([#639](https://github.com/cyverse/atmosphere/pull/639))
  - Linter runs more strict. Many changes were made to satisfy linter.
    ([#664](https://github.com/cyverse/atmosphere/pull/664))
  - Upgrade chromogenic from 0.4.18 to 0.4.20
    ([#670](https://github.com/cyverse/atmosphere/pull/670))
  - Upgrade django-cyverse-auth to 1.1.6 from 1.1.4
  ([#671](https://github.com/cyverse/atmosphere/pull/671))

### Removed
  - Remove code/vars related to old allocation system
    ([#656](https://github.com/cyverse/atmosphere/pull/656))
  - Removed references to selected_identity
    ([#639](https://github.com/cyverse/atmosphere/pull/639))

### Fixed
  - Consecutive test runs would fail because django-memoize was intercepting
    cassette playback ([#626](https://github.com/cyverse/atmosphere/pull/626))
  - Increased hard timeouts for tasks
    ([#650](https://github.com/cyverse/atmosphere/pull/650))
  - Variable changes to DJANGO_DEBUG and SEND_EMAILS
    ([#649](https://github.com/cyverse/atmosphere/pull/649))
  - Fixed v2 volume detach throwing 500 serialization error
    ([#655](https://github.com/cyverse/atmosphere/pull/655))
  - Reincluded/fixed broken tests
    ([#657](https://github.com/cyverse/atmosphere/pull/657))
  - In application_to_provider,py, determine correct upload method based
    on Glance client version specified in main function
    ([#667](https://github.com/cyverse/atmosphere/pull/667))

## [v33-0](https://github.com/cyverse/atmosphere/compare/v32-2...v33-0) - 2018-08-06
### Changed
  - Private networking resources (fixed IP, port, private subnet, private
    network) are preserved for inactive (suspended, shelved, stopped)
    instances ([#608](https://github.com/cyverse/atmosphere/pull/608))
    - Additionally atmosphere no longer reports the private ip in the absence
      of the public ip
  - `monitor_machines` periodic task runs once each night rather than every 30
    minutes ([#625](https://github.com/cyverse/atmosphere/pull/625))
  - Subspace is replaced by Ansible's PlaybookCLI for instance deployment
    ([#631](https://github.com/cyverse/atmosphere/pull/631))
  - Projects can be deleted if they only contain links/applications
    ([#640](https://github.com/cyverse/atmosphere/pull/640))

### Removed
  - In the general feedback email we no longer include the users selected
    provider, as it's no longer relevant
    ([#603](https://github.com/cyverse/atmosphere/pull/603))

### Fixed
  - Deleting a project via api/v2/projects no longer deletes enddated
    instances and volumes in those projects
    ([#640](https://github.com/cyverse/atmosphere/pull/640))
  - `application_to_provider` was using an invalid method in Glance Client v1
    to upload image data
    ([#618](https://github.com/cyverse/atmosphere/pull/618))
  - monitor_machines_for fails in the presence of inactive provider
    ([#614](https://github.com/cyverse/atmosphere/pull/614))
  - Chromogenic (0.4.17) had a caching issue causing imaging to fail
    ([#619](https://github.com/cyverse/atmosphere/pull/619))
  - Explicitly specify external network to rtwo when associating a floating IP
    address ([#624](https://github.com/cyverse/atmosphere/pull/624))
    ([#632](https://github.com/cyverse/atmosphere/pull/632))
  - Attaching task succeeded before volume was actually attached causing
    volume mount to fail
    ([#629](https://github.com/cyverse/atmosphere/pull/629))
  - Fix incorrect fetching of instances, upgrade to rtwo version 0.5.22
    ([#641](https://github.com/cyverse/atmosphere/pull/641))

## [v32-2](https://github.com/cyverse/atmosphere/compare/v32-1...v32-2) - 2018-04-26
### Fixed
  - Quota updates concerning volumes would silently fail
    ([#611](https://github.com/cyverse/atmosphere/pull/611))
  - Fix monitor_instances_for timing out, upgrade to rtwo version 0.5.18
    ([#598](https://github.com/cyverse/atmosphere/pull/598))
  - Fix unintentional fetch of all_tenants instances, upgrade to rtwo version
    0.5.19 ([#614](https://github.com/cyverse/atmosphere/pull/614))

## [v32-1](https://github.com/cyverse/atmosphere/compare/v32-0...v32-1) - 2018-04-17
### Added
  - Support multiple hostnames for Atmosphere(1) server
    ([#602](https://github.com/cyverse/atmosphere/pull/602))

### Fixed
  - On start/unshelve instances would fail to be reachable because ports added
    post boot ([#604](https://github.com/cyverse/atmosphere/pull/604))
  - Quota update would yield an index out of bounds error
    ([#606](https://github.com/cyverse/atmosphere/pull/606))
  - Travis build failure, specify version 9 of pip until we're ready for pip
    10 ([#607](https://github.com/cyverse/atmosphere/pull/607))

## [v32-0](https://github.com/cyverse/atmosphere/compare/v31-1...v32-0) - 2018-04-03
### Changed
### Added
  - Include a start date in the resource request api

### Changed
  - Update license to 2018
  - Update CHANGELOG.md to use the recommendations from [Keep a
    Changelog](http://keepachangelog.com/en/1.0.0/)
  - Change ./manage.py maintenance to be non-interactive
  - Return less information in the version api (api/v{1,2}/version) like
    atmosphere's major minor and patch version

### Fixed
  - The version reported for atmopshere ansible (api/v{1,2}/deploy_version now
  returns results

## [v31-1](https://github.com/cyverse/atmosphere/compare/v31-0...v31-1) - 2018-04-03
### Fixed
  - Worked around nova bug which prevented unshelved instances from getting
    fixed ips [#599](https://github.com/cyverse/atmosphere/pull/599)

## [v31-0](https://github.com/cyverse/atmosphere/compare/v30...v31-0) - 2018-03-08
### Added
  - Allow volumes and instances to be filtered by provider_id

### Changed
  - Update guacamole connection id to accept new un-truncated connection id
  - Remove our linting exceptions so we're linting more
  - Support new image visibility semantics in Glance API version 2.5
  - Small improvements to run_tests_like_travis.sh script
    - Create virtualenv if it doesn't exist
    - Install pip tools like travis

### Removed
  - Remove support for nginx/uwsgi (its now part of clank)

### Fixed
  - Fix image scripts not being included during deploy
  - Fix incorrect image actions are allowed during 'active - deploy_error',
    'shelved_offloaded', and 'shelved'

## [v30](https://github.com/cyverse/atmosphere/compare/v29...v30) - 2017-11-21
### Added
  - Site operators can override enforcement behavior for specific allocation sources

### Changed
  - Admin improvements
    - On resource request approval the reason field is omitted, which makes
      much more sense in the email template
    - Identities can be patched (to update quota)
  - Allocations now renews on first day of month
  - Multiple metadata syncing fixes:
    - `application_to_provider` previously did not migrate custom image
      metadata
    - `application_sync_providers` previously only looked at active
      (non-end-dated) InstanceSources + ProviderMachines
    - Refactored the part of `application_to_provider` which sets metadata,
      for less code duplication

### Fixed
  - Quota cannot exceed limit
  - Incorrect URL definition for web desktop/shell links
  - Missing DOI on ImageVersion model
  - Fixes to monitor_machines and validation
    - Legacy clouds need to call 'list images' twice and append info to the v2
      api.
    - Skip machines if their status is 'queued' or 'saving'
  - Various small bug fixes like undefined variables and attributes

## [Carbonaceous-Comet (v29)](https://github.com/cyverse/atmosphere/milestone/16?closed=1) - 2017-11-09
### Added
  - Site operators can now create machine validation plugins to control the
    flow of images in the atmosphere image catalog.
  - Users can now select a `guacamole_color` in their UserProfile, which will
    correspond to the theme used in guacamole web shell sessions.
  - Update travis to include code linting
  - Enable auto reload for uwsgi as an option for configuration.

### Changed
  - Change the location of ephemeral drives to a /scratch directory with a
    'data-loss' warning.
  - Explicitly pass the ssh IdentityFile to be used for instance_deploy and
    check_networking tasks.

### Fixed
  - Remove special characters from BootScripts prior to deployment.
  - Suspend instances if the ephemeral storage is set to /home directory and a
    'Shelve' action is received.

### Removed
  - Remove 'Provider' examples from the list of fixtures installed on a fresh
    database.
  - Celery init.d scripts are no longer included in Atmosphere. Use clank for
    installation/configuration of celery.

## [Beneficent-Bolide(v28)](https://github.com/cyverse/atmosphere/milestone/15?closed=1) - 2017-10-03
### Added
  - Users can now set 'access_list' on an application to specify an
    email/username pattern. Users that match the pattern will be added to
    present/future versions of the application.
  - Create a new 'AccountCreationPlugin' for direct Openstack logins
  - Introduced code coverage via coveralls
  - Provided instance 'fault' information when instance fails to deploy
  - Introduced new manage.py command to start/stop a maintenance

### Changed
  - Replaced time-series metrics with summarized metrics
  - BootScript support for strategies: run on first launch and run each
    deployment
  - BootScripts can be executed asynchronously. (Default is sync and return
    exit codes to user as a failure)
  - Ansible-ized user boot scripts
  - Celery now runs non-imaging tasks under user 'www-data'
  - Changed how atmosphere handles 'new_relic' settings and installation via
    clank.
  - Behave will be quieter in travis.ci

### Fixed
  - Temporary fix provided for updating multiple providers via single
    ResourceRequest
  - Fix provided for re-associating floating IP when an instance has two fixed
    IPs available.

### Removed
  - Removed all libcloud deployments. All instance deployments happen with
    ansible now!:tada:

## [Ancient-Asteroid(v27)](https://github.com/cyverse/atmosphere/milestone/14?closed=1) - 2017-09-19
### Added
  - Provide support to reset renewal date for allocation sources

### Changed
  - Ansible will now deploy user-boot-scripts
  - API /v2/sizes includes 'root' attribute (Root disk size)
  - Squashed migrations 0001-0084
  - Updated regression test-cases
  - Optimized resource request serialization to avoid slow API calls
  - Default to deployment when using v2 instance API for creating instances
  - Update the meaning of 'active' provider. Allow inactive providers to show
    resources but not be used for instance launch.

### Fixed
  - Fix broken emulation endpoint
  - Fixed a race-condition that would cause failures inside
    django-cyverse-auth
  - Cleanup formatting and variable definitions in project sharing feature
  - /v1/project_serializer includes previously-missing value 'created_by'
  - Remove unnecessary check for permissions on volume POST
  - Fix small edge-case where InstanceSource exists, but volume does not
  - Fix broken test-cases
  - Remove duplicated import
  - Fixed a bug where API was trying to return AsyncResult.
  - Fix web_token API calls
  - Small bugfix to /v2/volume API POST calls
  - Fixed a bug where missing snapshot will break
    `monitor_allocation_sources`.
  - Bug encountered and fixed related to Account emulation for staff users
  - ProjectVolume API fixed to work for v27 (will be removed in the future)
  - Include hotfix for `get_or_create_[user/token]` in django-cyverse-auth

### Removed
  - Remove unused v2 Event API
  - /api/v2/allocations has been removed
  - identity.allocation, and quota.allocation have been removed

## [Zesty-Zapdos](https://github.com/cyverse/atmosphere/milestone/13?closed=1) - 2017-07-17
### Added
 - Improvements to travis.yml to help improve the QOL working on the codebase.
 - Documentation on generating requirements in atmosphere
 - Prepare for Ubuntu 16.04 support with systemd scripts
 - Include script for generating instance reporting
 - Include script for replication of an application to a provider

### Changed
 - Disable instance sizes if the hosting image has a disk size thats larger
   than what is allowed.
   - Update the size attribute during monitoring of images
 - Releasing a new SSH client and VNC client -- Guacamole
   - Provide a simple API endpoint that allows new clients to decide on the
     functionality and return to Troposphere.
 - Invalid host headers disabled at nginx
 - Improve the onboarding process for new cloud providers by including sample
   cloud_config

### Fixed
 - Instances end dated at the point in time when deletion occurs in the API,
   rather than by request.
 - Fixed an error that caused legacy clouds to fail with "project_id" KeyError
 - Fixed an error that caused the wrong 'type' of quota value to be set on
   legacy and new clouds.

## [Yampy-Yellowlegs](https://github.com/cyverse/atmosphere/milestone/12?closed=1) - 2017-06-12
### Added
 - New script created to help migrate an entire application to a new provider

### Changed
 - Improvements related to the new Allocation Source model introduced in Xenops
 - Support for "Special allocations"
 - Move web_desktop functionality to Atmosphere from Troposphere

### Fixed
 - Time-sync issues caused the API to perform unexpectedly, fixed by adjusting
   only_current
 - Multiple bugs fixed related to the new Allocation Source model introduced
   in Xenops

## [Xylotomous-Xenops](https://github.com/cyverse/atmosphere/milestone/11?closed=1) - 2017-05-02
### Changed
 - Updated Atmosphere to latest subspace Ansible 2.3
   (https://github.com/cyverse/atmosphere/commit/253bf6d23ab1be0e15f35d97fa9a2b238b9bc639)
 - Jetstream fixes to allocation source model
 - Include shelve/unshelve instance actions.
 - Sourceid removed from Allocation Source model
 - Populate glance image metadata application_tags with valid JSON

### Fixed
 - Fixed application tags
   (https://github.com/cyverse/atmosphere/commit/fed9aae578025d8024f4a255ee109e12f1ff0483)
 - Behave fail for allocation settings
   (https://github.com/cyverse/atmosphere/commit/62686fd387203e2b5abe057d807503eabbddade4)
 - Unknown sizes appear when sizes are disabled
   (https://github.com/cyverse/atmosphere/pull/321)
 - Fixed duplicate `user_allocation_source` events
   (https://github.com/cyverse/atmosphere/issues/350)
   - Also has a migration to delete old duplicate events
 - Fix for umount && imaging, remove un-necessary lines in /etc/fstab
 - Bail out conditions for Celery task when MockDriver is used

## [Whimsical-Wyvern](https://github.com/cyverse/atmosphere/milestone/10?closed=1) - 2017-04-06
### Added
  - Include sentry.io error reporting for production environments
  - [application_to_provider](https://github.com/cyverse/atmosphere/pull/284)
    migration script
  - [iRODS transfer support](https://github.com/cyverse/atmosphere/pull/318)
    for application_to_provider script
  - A new image metrics API endpoint has been created (Staff-users only, for
    now)
  - Included redeploy as an InstanceAction

### Changed
  - Improved support for Instance Actions in v2 APIs
  - Include ext4 support for creating and mounting volumes
  - Upgrade to latest requirements.txt
  - Set provider quota returns more information to allow easier triage by
    support staff
  - Use ansible to create and mount volumes
  - Provide optional cloud_config options in 'deploy' section:
    'volume_fs_type' and 'volume_mount_prefix'
  - Image validation is now a feature flag, configurable from
    settings.ENABLE_IMAGE_VALIDATION

### Fixed
  - Enable LDAP Expiration information in Profile, if included in
    configuration

## [Voracious-Velociraptor](https://github.com/cyverse/atmosphere/milestone/9?closed=1) - 2017-02-14
### Added
  - Image validation works as intended (and deletes instance on cleanup)
  - New command `manage.py find_uuid` can help understand what object you are
    looking at when given a UUID without context
  - Improved sorting for image catalog
  - Include 'project' in instance launch (v2 API)

### Fixed
  - Instance status/activity show up as expected when in 'Networking' and
    'Deploying'
  - Errors that bubble up from API are now more verbose and help users
    understand the problem
  - Remove iPlant-isms from template pages
  - Fix logfile growing pains

## Undulating-Umbrellabird - 2017-01-04
### Added
  - move from iplantauth to django_cyverse_auth
  - Add 'user expiration' LDAP plugin and include 'is_expired' attribute in
    user's profile API
  - [Creation of new identities/providers now available in v2
    API](https://github.com/cyverse/atmosphere/pull/222)
  - Include instance reporting as a v2 API, allow generation of XLSX and CSV
    files
  - Create a PluginManager to avoid code duplication between plugin validation
    and class loading

### Fixed
  - Fixed a bug that caused the image bookmark API to produce an invalid query
  - Quota foreign key has been re-assigned from IdentityMembership to Identity
  - Create router gateway when using the ExternalNetworkTopology
  - Quota can now be set "above the pre-set limits" listed in openstack.

### Deprecated
  - [./scripts/add_new_accounts.py](./scripts/add_new_accounts.py) and
    [./scripts/add_new_provider.py](./scripts/add_new_provider.py) will stop
    receiving updates after creation is moved into the GUI/API.
