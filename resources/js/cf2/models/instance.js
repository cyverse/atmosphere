Atmo.Models.Instance = Atmo.Models.Base.extend({

        defaults: { 'model_name': 'instance' },
        initialize: function() {
                this.set('name_or_id', this.get('name') || this.get('id'));
                this.set('launch_relative', Atmo.Utils.relative_time(this.get('launch_time')));
        },
        parse: function(response) {
                var attributes = response;

                attributes.description = response.name;
                attributes.id = response.alias;
                attributes.name = response.name;
                attributes.image_id = response.machine_alias;
                attributes.image_name = response.machine_name;
                attributes.image_hash = response.alias_hash;
                attributes.image_url = Atmo.profile.get_icon(response.machine_alias_hash);
                attributes.type = response.size_alias;
                attributes.launch_time = new Date(response.start_date);
                attributes.state = response.status;
                attributes.has_shall = response.has_shell;
                attributes.has_vnc = response.has_vnc;
                if (response.ip_address == "0.0.0.0" && response.status == "active") {
                        response.status = "active - networking";
                        attributes.state = "active - networking";
                }
                //NOTE: Shouldn't this be attributes.state, instead?
                attributes.state_is_active = (   response.status == 'active'
                                                        || response.status == 'running'
                                                        || response.status == 'verify_resize' );
                attributes.state_is_build = (        response.status == 'build'
                                                        || response.status == 'build - block_device_mapping'
                                                          || response.status == 'build - scheduling'
                                                          || response.status == 'build - spawning'
                                                        || response.status == 'build - networking'
                                                        || response.status == 'active - powering-off'
                                                        || response.status == 'active - image_uploading'
                                                        || response.status == 'shutoff - powering-on'
                                                        || response.status == 'pending'
                                                        || response.status == 'suspended - resuming'
                                                        || response.status == 'active - suspending'
                                                        || response.status == 'resize - resize_prep'
                                                        || response.status == 'resize - resize_migrating'
                                                        || response.status == 'resize - resize_migrated'
                                                        || response.status == 'resize - resize_finish'
                                                        || response.status == 'active - networking'
                                                        || response.status == 'active - deploying'
                                                        || response.status == 'active - initializing'
                                                        || response.status == 'hard_reboot - rebooting_hard'
                                                        || response.status == 'revert_resize - resize_reverting' );
                attributes.state_is_delete = (        response.status == 'delete'
                                                          || response.status == 'active - deleting'
                                                        || response.status == 'deleted'
                                                        || response.status == 'shutting-down'
                                                        || response.status == 'terminated' );
                attributes.state_is_inactive = (        response.status == 'suspended'
                                                        || response.status == 'shutoff');
                attributes.private_dns_name = response.ip_address;
                attributes.public_dns_name = response.ip_address;

                if(response.status === 'error'){
                    attributes.state = 'Atmosphere is at capacity. Please retry later.';
                    //attributes.status = attributes.state;
                }
                return attributes;
        },
        confirm_terminate: function(options) {
                var header = "Are you sure you want to terminate this instance?";
                var body = '<p class="alert alert-error"><i class="icon-warning-sign"></i> <b>WARNING</b> Unmount volumes within your instance '
                        + 'before terminating or risk corrupting your data and the volume.</p>'
                        + "<p>Your instance <strong>" + this.get('name') + " #" + this.get('id') + "</strong> will be shut down and all data will be permanently lost!</p>"
                        + "<p><u>Note:</u> Your resource usage charts will not reflect changes until the instance is completely terminated and has disappeared from your list of instances.</p>";

                var self = this;

                Atmo.Utils.confirm(header, body, {
                        on_confirm : function() {

                                Atmo.Utils.notify('Terminating Instance...', 'Please wait while your instance terminates.');

                                self.destroy({
                                        wait: true,
                                        success: options.success,
                                        error: options.error
                                });
                        },
                        ok_button: 'Yes, terminate this instance'
                });
        },
        select: function() {
                this.collection.select_instance(this);
        },
        destroy: function(options) {
                // We overwrite the destroy function so that the model doesn't get deleted while the instance is still 'terminating'

                options = options ? _.clone(options) : {};
                var model = this;
                var success = options.success;

                var self = this;
                options.success = function(resp) {
                        if (success) {
                                success(model, resp, options);

                                // Get the new state from the data returned by API call
                                self.set('state', resp.status);
                        }

                        if (!model.isNew())
                                model.trigger('sync', model, resp, options);
                };

                // wrapError function from backbone.js
                var wrapError = function (model, options) {
                        var error = options.error;
                        options.error = function(resp) {
                                if (error) error(model, resp, options);
                                model.trigger('error', model, resp, options);
                        };
                };

                if (this.isNew()) {
                        options.success();
                        return false;
                }

                wrapError(this, options);

                var xhr = this.sync('delete', this, options);
                return xhr;
        }
});

_.extend(Atmo.Models.Instance.defaults, Atmo.Models.Base.defaults);
