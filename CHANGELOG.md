## [Delightful-Duboshin (v30)](https://github.com/cyverse/atmosphere/milestone/17?closed=1) (as of 2017-12-21)

New Features:
- Site operators can override enforcement behavior for specific allocation sources

Improvements:
- Admin improvements
    - On resource request approval the reason field is omitted, which makes much more sense in the email template
    - Identities can be patched (to update quota)
- Allocations now renews on first day of month   
- Multiple metadata syncing fixes:
    - `application_to_provider` previously did not migrate custom image metadata
    - `application_sync_providers` previously only looked at active (non-end-dated) InstanceSources + ProviderMachines
    - Refactored the part of `application_to_provider` which sets metadata, for less code duplication
    
Bugfixes:
- Quota cannot exceed limit
- Incorrect URL definition for web desktop/shell links
- Missing DOI on ImageVersion model
- Fixes to monitor_machines and validation
    - Legacy clouds need to call 'list images' twice and append info to the v2 api.
    - Skip machines if their status is 'queued' or 'saving'
- Various small bug fixes like undefined variables and attributes


## [Carbonaceous-Comet (v29)](https://github.com/cyverse/atmosphere/milestone/16?closed=1) (as of 2017-11-09)

New Features:
- Site operators can now create machine validation plugins to control the flow of images in the atmosphere image catalog.
- Users can now select a `guacamole_color` in their UserProfile, which will correspond to the theme used in guacamole web shell sessions.

Bugfixes:
- Remove special characters from BootScripts prior to deployment.
- Suspend instances if the ephemeral storage is set to /home directory and a 'Shelve' action is received.

Internal:
- Change the location of ephemeral drives to a /scratch directory with a 'data-loss' warning.
- Remove 'Provider' examples from the list of fixtures installed on a fresh database.
- Explicitly pass the ssh IdentityFile to be used for instance_deploy and check_networking tasks.
- Update travis to include code linting
- Enable auto reload for uwsgi as an option for configuration.
- Celery init.d scripts are no longer included in Atmosphere. Use clank for installation/configuration of celery.


## [Beneficent-Bolide(v28)](https://github.com/cyverse/atmosphere/milestone/15?closed=1) (as of 2017-10-03)

New Features:
- Users can now set 'access_list' on an application
  to specify an email/username pattern. Users that
  match the pattern will be added to present/future
  versions of the application.

Improvements:
- Replaced time-series metrics with summarized metrics
- BootScript support for strategies: run on first launch and run each deployment
- BootScripts can be executed asynchronously. (Default is sync and return exit codes to user as a failure)

Bugfixes:
- Temporary fix provided for updating multiple providers via single ResourceRequest
- Fix provided for re-associating floating IP when an instance has two fixed IPs available.

Internal:
- Ansible-ized user boot scripts
- Removed all libcloud deployments. All instance deployments happen with ansible now!:tada:
- Create a new 'AccountCreationPlugin' for direct Openstack logins
- Celery now runs non-imaging tasks under user 'www-data'
- Introduced code coverage via coveralls
- Provided instance 'fault' information when instance fails to deploy
- Changed how atmosphere handles 'new_relic' settings and installation via clank.
- Introduced new manage.py command to start/stop a maintenance
- Behave will be quieter in travis.ci


## [Ancient-Asteroid(v27)](https://github.com/cyverse/atmosphere/milestone/14?closed=1) (as of 2017-09-19)

Improvements:
- Ansible will now deploy user-boot-scripts
- API /v2/sizes includes 'root' attribute (Root disk size)

Bugfixes:
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

Internal:
- Squash migrations 0001-0084
- cleanup migration 0092
- Remove unused v2 Event API
- Updated regression test-cases
- Optimized resource request serialization to avoid slow API calls
- Bug encountered and fixed related to Account emulation for staff users
- ProjectVolume API fixed to work for v27 (will be removed in the future)
- Default to deployment when using v2 instance API for creating instances
- Include hotfix for `get_or_create_[user/token]` in django-cyverse-auth
- Update the meaning of 'active' provider. Allow inactive providers to show resources
  but not be used for instance launch.
- Provide support to reset renewal date for allocation sources

Deprecated:
  - /api/v2/allocations has been removed
  - identity.allocation, and quota.allocation have been removed

## [Zesty-Zapdos](https://github.com/cyverse/atmosphere/milestone/13?closed=1) (as of 2017-07-17)

Improvements:
 - Disable instance sizes if the hosting image has a disk size thats larger than what is allowed.
   - Update the size attribute during monitoring of images
 - Releasing a new SSH client and VNC client -- Guacamole
   - Provide a simple API endpoint that allows new clients to decide on the functionality and return to Troposphere.

Bugfixes:
 - Instances end dated at the point in time when deletion occurs in the API, rather than by request.
 - Fixed an error that caused legacy clouds to fail with "project_id" KeyError
 - Fixed an error that caused the wrong 'type' of quota value to be set on legacy and new clouds.

Internal:
 - Invalid host headers disabled at nginx
 - Improvements to travis.yml to help improve the QOL working on the codebase.
 - Documentation on generating requirements in atmosphere
 - Improve the onboarding process for new cloud providers by including sample cloud_config
 - Prepare for Ubuntu 16.04 support with systemd scripts
 - Include script for generating instance reporting
 - Include script for replication of an application to a provider


## [Yampy-Yellowlegs](https://github.com/cyverse/atmosphere/milestone/12?closed=1) (as of 2017-06-12)

Improvements:
 - Improvements related to the new Allocation Source model introduced in Xenops
 - Support for "Special allocations"


Bugfixes:
 - Time-sync issues caused the API to perform unexpectedly, fixed by adjusting only_current
 - Multiple bugs fixed related to the new Allocation Source model introduced in Xenops

Internal:
 - Move web_desktop functionality to Atmosphere from Troposphere
 - New script created to help migrate an entire application to a new provider

## [Xylotomous-Xenops](https://github.com/cyverse/atmosphere/milestone/11?closed=1) (as of 2017-05-02)
 
Improvements:
 - Updated Atmosphere to latest subspace Ansible 2.3 (https://github.com/cyverse/atmosphere/commit/253bf6d23ab1be0e15f35d97fa9a2b238b9bc639)
 - Jetstream fixes to allocation source model
 - Include shelve/unshelve instance actions.

 
Bugfixes:
 - Fixed application tags (https://github.com/cyverse/atmosphere/commit/fed9aae578025d8024f4a255ee109e12f1ff0483)
 - Behave fail for allocation settings (https://github.com/cyverse/atmosphere/commit/62686fd387203e2b5abe057d807503eabbddade4)
 - Unknown sizes appear when sizes are disabled (https://github.com/cyverse/atmosphere/pull/321)
 - Fixed duplicate `user_allocation_source` events (https://github.com/cyverse/atmosphere/issues/350)
   - Also has a migration to delete old duplicate events
 - Fix for umount && imaging, remove un-necessary lines in /etc/fstab
 
Internal:
 - Bail out conditions for Celery task when MockDriver is used
 - Sourceid removed from Allocation Source model
 - Populate glance image metadata application_tags with valid JSON
 
 

## [Whimsical-Wyvern](https://github.com/cyverse/atmosphere/milestone/10?closed=1) (as of 2017-04-06)

Features:
  - Include sentry.io error reporting for production environments
  - [application_to_provider](https://github.com/cyverse/atmosphere/pull/284) migration script
  - [iRODS transfer support](https://github.com/cyverse/atmosphere/pull/318) for application_to_provider script

Improvements:
  - Improved support for Instance Actions in v2 APIs
  - Include ext4 support for creating and mounting volumes

Bugfixes:
  - Set provider quota returns more information to allow easier triage by support staff
  - Enable LDAP Expiration information in Profile, if included in configuration

Internal:
  - A new image metrics API endpoint has been created (Staff-users only, for now)
  - Upgrade to latest requirements.txt
  - Included redeploy as an InstanceAction
  - Use ansible to create and mount volumes
  - Provide optional cloud_config options in 'deploy' section: 'volume_fs_type' and 'volume_mount_prefix'
  - Image validation is now a feature flag, configurable from settings.ENABLE_IMAGE_VALIDATION

## [Voracious-Velociraptor](https://github.com/cyverse/atmosphere/milestone/9?closed=1) (as of 2017-02-14)

Features:
  - Image validation works as intended (and deletes instance on cleanup)
  - New command `manage.py find_uuid` can help understand what object you are looking at when given a UUID without context
  - Improved sorting for image catalog
  - Include 'project' in instance launch (v2 API)

Bugfixes:
  - Instance status/activity show up as expected when in 'Networking' and 'Deploying'
  - Errors that bubble up from API are now more verbose and help users understand the problem

Internal:
  - Remove iPlant-isms from template pages
  - Fix logfile growing pains

## Undulating-Umbrellabird (as of 2017-01-04)

Features:
  - move from iplantauth to django_cyverse_auth
  - Add 'user expiration' LDAP plugin and include 'is_expired' attribute in user's profile API
  - [Creation of new identities/providers now available in v2 API](https://github.com/cyverse/atmosphere/pull/222)
  - Include instance reporting as a v2 API, allow generation of XLSX and CSV files
  - Create a PluginManager to avoid code duplication between plugin validation and class loading

Bugfixes:
  - Fixed a bug that caused the image bookmark API to produce an invalid query
  - Quota foreign key has been re-assigned from IdentityMembership to Identity
  - Create router gateway when using the ExternalNetworkTopology
  - Quota can now be set "above the pre-set limits" listed in openstack.

Deprecated:
  - [./scripts/add_new_accounts.py](./scripts/add_new_accounts.py) and [./scripts/add_new_provider.py](./scripts/add_new_provider.py) will stop receiving updates after creation is moved into the GUI/API.

## Toco-Toucan

Internal Release:
  - Included in `Undulating-Umbrellabird`
