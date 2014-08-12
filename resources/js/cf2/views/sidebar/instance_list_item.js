Atmo.Views.SidebarInstanceListItem = Backbone.View.extend({
    tagName: 'li',
    className: 'instance_rect media',
    template: _.template(Atmo.Templates.sidebar_instance_list_item),
    events: {
        'click' : 'rect_clicked',
        'click .rect-delete': 'terminate',
        'click .terminate_shell': 'close_shell',
        'click .terminate_vnc': 'close_vnc'
    },
    initialize: function() {
      this.in_task = false;
      this.$el.data('instance', this.model);
      this.model.bind('change:public_dns_name change:name_or_id change', this.render, this);
      this.model.bind('change:running_shell', this.update_running_state, this);
      this.model.bind('change:running_vnc', this.update_running_state, this);
      this.model.bind('change:state', this.trigger_transition, this);
          Atmo.instances.bind('select', this.highlight, this);
    },
    render: function() {

        var self = this;

        // Re-applying the template every time causes the instance list to flash and re-create the list every time.
        if (!this.rendered) {
            this.$el.attr('data-instanceid', this.model.get('id'));
            this.$el.html(this.template(this.model.toJSON()));
        }
        else {
            // Otherwise, we want to update as little data as has actually changed.
            // Don't want a huge, flashy re-render

            // Update name or id, if needed
            if (this.$el.find('.media-body b').html() != this.model.get('name_or_id')) {
                this.$el.find('.media-body b').html(this.model.get('name_or_id'));
            }

            // Update IP address, if needed
            if (this.$el.find('.media-body span').html() != this.model.get('public_dns_name')) {
                this.$el.find('.media-body span').html(this.model.get('public_dns_name'));
            }
            
            // Update running state if needed
            this.$el.find('.instance_state').attr('class', 'instance_state');
            this.$el.find('.instance_state').html('Instance status: ' + this.model.get('state'));
        }

        var ip_addr_span = this.$el.find('.media-body span');
        if (this.model.get('public_dns_name') == "0.0.0.0") {
            //Clear the IP address field
            ip_addr_span.html("");
        }
        if (this.model.get('selected')) {
            this.$el.addClass('active');
        }
        this.update_running_state();

        // Use the provider generic states: 'active', 'build', 'delete'
        this.$el.find('.instance_state').addClass(function() {
            var states = ['active', 'inactive', 'build', 'delete'];
            for (var i = 0; i < states.length; i++) {
                if (self.model.get('state_is_'+states[i]))
                    return 'instance_state_is_' + states[i];
            }
            return 'instance_state_is_delete';        // If none of the instance states are true, assume it's an error
        });

        setTimeout(function() {
            self.$el.find('div').slideDown();
        }, 1500);

        this.rendered = true;

        if (this.model.get('state').indexOf('-') != -1)
            this.trigger_transition();

        return this;
    },
    highlight: function(model) {
        if (this.model == model)
            this.$el.addClass('active');
        else 
            this.$el.removeClass('active');
    },
    rect_clicked: function() {
        this.model.select();    
    },
    close_shell: function() {
        this.model.set('running_shell', false);
    },
    close_vnc: function() {
        this.model.set('running_vnc', false);
    },
    update_running_state: function() {
        this.$el.find('.instance_service').remove();
        var self = this;
        $.each(['Shell', 'VNC'], function(k, service) {
            var service_lower = service.toLowerCase();
            if (self.model.get('running_' + service_lower))
                $('<li/>', {
                    'class': 'instance_service',
                    html: service + ' is running'
                }).append($('<img/>', { 
                        src: site_root+'/resources/images/x_close.png',
                        'class': 'terminate_' + service_lower
                })).appendTo(self.$el.find('.instance_state_indicators'));
        });
    },
    terminate: function(e) {
        e.stopPropagation();

        var instances = this.model.collection;
        
        if (this.model.get('state_is_delete') == true) {
            Atmo.Utils.notify("Please wait", "Instance status is already " + this.model.get('state') + ".");
            return false;
        }
        else {
            this.model.confirm_terminate({
                success: function() {
                    instances.update();

                    var header = 'Instance terminated';
                    var body = '';
                    Atmo.Utils.notify(header, body);
                },
                error: function() {
                    Atmo.Utils.notify("Could not delete this instance", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
                },
            });
        }
    },
    trigger_transition: function() {


        // Deal with non-task states
        var self = this;
        if (!this.rendered) {
            this.$el.attr('data-instanceid', this.model.get('id'));
            this.$el.html(this.template(this.model.toJSON()));
        }
        else {
            // Update state if needed
            this.$el.find('.instance_state').attr('class', 'instance_state');
            this.$el.find('.instance_state').html('Instance status: ' + this.model.get('state'));
        }
        this.rendered = true;

        // Use the provider generic states: 'active', 'build', 'delete' to determine indicator color
        this.$el.find('.instance_state').addClass(function() {
            var states = ['active', 'inactive', 'build', 'delete'];
            for (var i = 0; i < states.length; i++) {
                if (self.model.get('state_is_'+states[i]))
                    return 'instance_state_is_' + states[i];
            }
            return 'instance_state_is_delete';        // If none of the instance states are true, assume it's an error
        });

        // If a task has already begun, jump to work on it
        if (this.in_task) {
            this.add_instance_task();
            return;
        }

        // Now, deal with task states -- initialize task format: 'state - task' 
        if (this.model.get('state').indexOf('-') != -1) {
            this.add_instance_task();

            setTimeout(function() {
                self.$el.find('div').slideDown();
            }, 1500);
        }
    },
    get_final_state: function(state, task) {
        // Check for the final state to prevent reverting if a queued task hasn't begun yet
        if (state == 'resize') {
            return 'verify_resize';
        }
        else if (task == 'powering-off') {
            return 'shutoff';
        }
        else if (task == 'deleting') {
            return 'deleted';
        }
        else if (task == 'suspending') {
            return 'suspended';
        }
        else if (task ==='deploy_error') {
            return 'deploy_error';
        }
        else {
            return 'active';
            // Applies for: hard_reboot, build, shutoff, suspended, and revert_resize
        }
    },
    add_instance_task: function() {
        // So we know not to override stuff if the API respond reverts to a non-task state
        this.in_task = true;

        var percent = 0;

        if (this.model.get('state').indexOf('-') == -1) {
            /* This can mean one of two things: 
                1. Instance has reached final state (it's 100% done)
                2. The instance hasn't been reached in the queue (it's 5% done)
            */
                percent = (this.final_state == this.model.get('state')) ? 100 : 5;

        }
        else {
            var parts = this.model.get('state').split('-');
            var state = parts[0].trim();
            var task = parts[1].trim();

            // Deal with Openstack Grizzly's silly hyphenated states "powering-on" and "powering-off"
            if (parts.length == 3)
                task = parts[1].trim() + '-' + parts[2].trim();

            percent = this.get_percent_complete(state, task);
            this.final_state = this.get_final_state(state, task);
        }
        if(this.final_state === 'deploy_error'){
            return
        }

        // Do initial update
        this.update_percent_complete(percent);

        // Initialize polling
        this.poll_instance();

    },
    update_percent_complete: function(percent) {

        var graph_holder, graph_bar, self = this;
        if (this.$el.find('.graphBar').length == 1) {
            graph_holder = this.$el.find('.graphBar');
            graph_bar = this.$el.find('[class$="GraphBar active"]');
            graph_bar.css('width', ''+percent+'%');
        }
        else {
            this.$el.find('.media-body').append($('<div>', {
                class: 'graphBar',
                style: 'height: 16px'
            }));
            graph_holder = this.$el.find('.graphBar');
            graph_holder.append($('<div>', {
                class: 'blueGraphBar active',
                width: '0%'
            }));
            graph_bar = graph_holder.children();
        }

        // Update if necessary
        setTimeout(function() {
            graph_bar.css('width', ''+percent+'%');
        }, 1.5 * 1000);

        if (percent == 100) {
            clearInterval(this.poll);
            this.poll = undefined;
            this.final_state = undefined;

            // Allow animation to complete, then hide graph bar
            setTimeout(function() {
                self.$el.find('.graphBar').slideUp('fast', function() {
                    $(this).remove();    
                });
            }, 2 * 1000);

            this.in_task = false;
        }
    },
    get_percent_complete: function(state, task) {
        var states = {
            'build' : {
                'block_device_mapping' : 10,            // Number represents percent task *completed* when in this state
                'scheduling' : 20,
                'networking' : 30,
                'spawning' : 40,
            },
            'reboot' : {
                'rebooting' : 50
            },
            'hard_reboot' : {
                'rebooting_hard' : 50
            },
            'resize' : {
                'resize_prep' : 10,
                'resize_migrating' : 20,
                'resize_migrated' : 40,
                'resize_finish' : 70,
                'verify_resize' : 90,
            },
            'active' : {
                'powering-off' : 50,
                'image_uploading' : 50,
                'deleting' : 50,
                'suspending' : 50,
                'initializing' :50,
                'networking' : 60,
                'deploying' : 70
            },
            'shutoff' : {
                'powering-on' : 50
            },
            'suspended' : {
                'resuming' : 50
            },
            'revert_resize' : {
                'resize_reverting' : 50
            }
        };

        return states[state][task];
    },
    poll_instance: function() {
        var self = this;

        if (!this.poll) {
            function poll_instances() {

                if (self.model.get('state') == self.final_state || self.final_state == undefined) {
                    self.poll = undefined;
                    clearInterval(self.poll);
                    return;
                }

                // Instance is done updating, has reached non-task state
                self.model.fetch({
                    error: function(xhr, textStatus, error) {

                        // Stop polling
                        clearInterval(self.poll);
                        self.in_task = false;
                        self.poll = undefined;

                        // Instance was deleted
                        if (textStatus.status == 404) {
                            self.update_percent_complete(100)
                            Atmo.instances.update();
                            return;
                        }
                        else {
                            self.update_percent_complete(0);
                            Atmo.Utils.notify('An error occurred', 'Could not retrieve instance information. Refresh or contact <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a> if the problem continues.');
                        }
                    }
                });
            }

            if (self.model.get('state') != self.final_state || self.final_state != undefined) {
                this.poll = setInterval(poll_instances, 60 * 1000);
            }
        }
    }
});
