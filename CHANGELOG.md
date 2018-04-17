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

## [Unreleased](https://github.com/cyverse/atmosphere/compare/v32-0...HEAD)
### Added
 - Support multiple hostnames for Atmosphere(1) server ([#602](https://github.com/cyverse/atmosphere/pull/602))

### Fixed
 - On start/unshelve instances would fail to be reachable because ports added
   post boot ([#604](https://github.com/cyverse/atmosphere/pull/604))
 - Quota update would yield an index out of bounds error ((606)[https://github.com/cyverse/atmosphere/pull/606])
 - Travis build failure, specify version 9 of pip until we're ready for pip 10 ((607)[https://github.com/cyverse/atmosphere/pull/607])

## [v32-0](https://github.com/cyverse/atmosphere/compare/v31-1...v32-0) 2018-04-03
### Changed
### Added
  - Include a start date in the resource request api

### Changed
  - Update license to 2018
  - Update CHANGELOG.md to use the recommendations from [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
  - Change ./manage.py maintenance to be non-interactive
  - Return less information in the version api (api/v{1,2}/version) like
    atmosphere's major minor and patch version

### Fixed
  - The version reported for atmopshere ansible (api/v{1,2}/deploy_version now
  returns results

## [v31-1](https://github.com/cyverse/atmosphere/compare/v31-0...v31-1) 2018-04-03
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
  - Fix incorrect image actions are allowed during 'active - deploy_error', 'shelved_offloaded', and 'shelved'

## [v30](https://github.com/cyverse/atmosphere/compare/v29...v30) - 2017-11-21
### Added
  - Site operators can override enforcement behavior for specific allocation sources

### Changed
  - Admin improvements
    - On resource request approval the reason field is omitted, which makes much more sense in the email template
    - Identities can be patched (to update quota)
  - Allocations now renews on first day of month
  - Multiple metadata syncing fixes:
    - `application_to_provider` previously did not migrate custom image metadata
    - `application_sync_providers` previously only looked at active (non-end-dated) InstanceSources + ProviderMachines
    - Refactored the part of `application_to_provider` which sets metadata, for less code duplication

### Fixed
  - Quota cannot exceed limit
  - Incorrect URL definition for web desktop/shell links
  - Missing DOI on ImageVersion model
  - Fixes to monitor_machines and validation
    - Legacy clouds need to call 'list images' twice and append info to the v2 api.
    - Skip machines if their status is 'queued' or 'saving'
  - Various small bug fixes like undefined variables and attributes

## [Carbonaceous-Comet (v29)](https://github.com/cyverse/atmosphere/milestone/16?closed=1) - 2017-11-09
### Added
  - Site operators can now create machine validation plugins to control the flow of images in the atmosphere image catalog.
  - Users can now select a `guacamole_color` in their UserProfile, which will correspond to the theme used in guacamole web shell sessions.
  - Update travis to include code linting
  - Enable auto reload for uwsgi as an option for configuration.

### Changed
  - Change the location of ephemeral drives to a /scratch directory with a 'data-loss' warning.
  - Explicitly pass the ssh IdentityFile to be used for instance_deploy and check_networking tasks.

### Fixed
  - Remove special characters from BootScripts prior to deployment.
  - Suspend instances if the ephemeral storage is set to /home directory and a 'Shelve' action is received.

### Removed
  - Remove 'Provider' examples from the list of fixtures installed on a fresh database.
  - Celery init.d scripts are no longer included in Atmosphere. Use clank for installation/configuration of celery.

## [Beneficent-Bolide(v28)](https://github.com/cyverse/atmosphere/milestone/15?closed=1) - 2017-10-03
### Added
  - Users can now set 'access_list' on an application to specify an email/username pattern. Users that match the pattern will be added to present/future versions of the application.
  - Create a new 'AccountCreationPlugin' for direct Openstack logins
  - Introduced code coverage via coveralls
  - Provided instance 'fault' information when instance fails to deploy
  - Introduced new manage.py command to start/stop a maintenance

### Changed
  - Replaced time-series metrics with summarized metrics
  - BootScript support for strategies: run on first launch and run each deployment
  - BootScripts can be executed asynchronously. (Default is sync and return exit codes to user as a failure)
  - Ansible-ized user boot scripts
  - Celery now runs non-imaging tasks under user 'www-data'
  - Changed how atmosphere handles 'new_relic' settings and installation via clank.
  - Behave will be quieter in travis.ci

### Fixed
  - Temporary fix provided for updating multiple providers via single ResourceRequest
  - Fix provided for re-associating floating IP when an instance has two fixed IPs available.

### Removed
  - Removed all libcloud deployments. All instance deployments happen with ansible now!:tada:

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
  - Update the meaning of 'active' provider. Allow inactive providers to show resources but not be used for instance launch.

### Fixed
  - Fix broken emulation endpoint
  - Fixed a race-condition that would cause failures inside django-cyverse-auth
  - Cleanup formatting and variable definitions in project sharing feature
  - /v1/project_serializer includes previously-missing value 'created_by'
  - Remove unnecessary check for permissions on volume POST
  - Fix small edge-case where InstanceSource exists, but volume does not
  - Fix broken test-cases
  - Remove duplicated import
  - Fixed a bug where API was trying to return AsyncResult.
  - Fix web_token API calls
  - Small bugfix to /v2/volume API POST calls
  - Fixed a bug where missing snapshot will break `monitor_allocation_sources`.
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
 - Disable instance sizes if the hosting image has a disk size thats larger than what is allowed.
   - Update the size attribute during monitoring of images
 - Releasing a new SSH client and VNC client -- Guacamole
   - Provide a simple API endpoint that allows new clients to decide on the functionality and return to Troposphere.
 - Invalid host headers disabled at nginx
 - Improve the onboarding process for new cloud providers by including sample cloud_config

### Fixed
 - Instances end dated at the point in time when deletion occurs in the API, rather than by request.
 - Fixed an error that caused legacy clouds to fail with "project_id" KeyError
 - Fixed an error that caused the wrong 'type' of quota value to be set on legacy and new clouds.

## [Yampy-Yellowlegs](https://github.com/cyverse/atmosphere/milestone/12?closed=1) - 2017-06-12
### Added
 - New script created to help migrate an entire application to a new provider

### Changed
 - Improvements related to the new Allocation Source model introduced in Xenops
 - Support for "Special allocations"
 - Move web_desktop functionality to Atmosphere from Troposphere

### Fixed
 - Time-sync issues caused the API to perform unexpectedly, fixed by adjusting only_current
 - Multiple bugs fixed related to the new Allocation Source model introduced in Xenops

## [Xylotomous-Xenops](https://github.com/cyverse/atmosphere/milestone/11?closed=1) - 2017-05-02
### Changed
 - Updated Atmosphere to latest subspace Ansible 2.3 (https://github.com/cyverse/atmosphere/commit/253bf6d23ab1be0e15f35d97fa9a2b238b9bc639)
 - Jetstream fixes to allocation source model
 - Include shelve/unshelve instance actions.
 - Sourceid removed from Allocation Source model
 - Populate glance image metadata application_tags with valid JSON

### Fixed
 - Fixed application tags (https://github.com/cyverse/atmosphere/commit/fed9aae578025d8024f4a255ee109e12f1ff0483)
 - Behave fail for allocation settings (https://github.com/cyverse/atmosphere/commit/62686fd387203e2b5abe057d807503eabbddade4)
 - Unknown sizes appear when sizes are disabled (https://github.com/cyverse/atmosphere/pull/321)
 - Fixed duplicate `user_allocation_source` events (https://github.com/cyverse/atmosphere/issues/350)
   - Also has a migration to delete old duplicate events
 - Fix for umount && imaging, remove un-necessary lines in /etc/fstab
 - Bail out conditions for Celery task when MockDriver is used

## [Whimsical-Wyvern](https://github.com/cyverse/atmosphere/milestone/10?closed=1) - 2017-04-06
### Added
  - Include sentry.io error reporting for production environments
  - [application_to_provider](https://github.com/cyverse/atmosphere/pull/284) migration script
  - [iRODS transfer support](https://github.com/cyverse/atmosphere/pull/318) for application_to_provider script
  - A new image metrics API endpoint has been created (Staff-users only, for now)
  - Included redeploy as an InstanceAction

### Changed
  - Improved support for Instance Actions in v2 APIs
  - Include ext4 support for creating and mounting volumes
  - Upgrade to latest requirements.txt
  - Set provider quota returns more information to allow easier triage by support staff
  - Use ansible to create and mount volumes
  - Provide optional cloud_config options in 'deploy' section: 'volume_fs_type' and 'volume_mount_prefix'
  - Image validation is now a feature flag, configurable from settings.ENABLE_IMAGE_VALIDATION

### Fixed
  - Enable LDAP Expiration information in Profile, if included in configuration

## [Voracious-Velociraptor](https://github.com/cyverse/atmosphere/milestone/9?closed=1) - 2017-02-14
### Added
  - Image validation works as intended (and deletes instance on cleanup)
  - New command `manage.py find_uuid` can help understand what object you are looking at when given a UUID without context
  - Improved sorting for image catalog
  - Include 'project' in instance launch (v2 API)

### Fixed
  - Instance status/activity show up as expected when in 'Networking' and 'Deploying'
  - Errors that bubble up from API are now more verbose and help users understand the problem
  - Remove iPlant-isms from template pages
  - Fix logfile growing pains

## Undulating-Umbrellabird - 2017-01-04
### Added
  - move from iplantauth to django_cyverse_auth
  - Add 'user expiration' LDAP plugin and include 'is_expired' attribute in user's profile API
  - [Creation of new identities/providers now available in v2 API](https://github.com/cyverse/atmosphere/pull/222)
  - Include instance reporting as a v2 API, allow generation of XLSX and CSV files
  - Create a PluginManager to avoid code duplication between plugin validation and class loading

### Fixed
  - Fixed a bug that caused the image bookmark API to produce an invalid query
  - Quota foreign key has been re-assigned from IdentityMembership to Identity
  - Create router gateway when using the ExternalNetworkTopology
  - Quota can now be set "above the pre-set limits" listed in openstack.

### Deprecated
  - [./scripts/add_new_accounts.py](./scripts/add_new_accounts.py) and [./scripts/add_new_provider.py](./scripts/add_new_provider.py) will stop receiving updates after creation is moved into the GUI/API.
