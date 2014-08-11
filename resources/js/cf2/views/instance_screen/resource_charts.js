/**
 *
 * Creates resource charts that can be used to determine whether or not a change in resource usage will cause the user
 * to exceed their quota.
 *
 */
Atmo.Views.ResourceCharts = Backbone.View.extend({
    initialize: function(options) {
        this.quota_type = options.quota_type; // REQUIRED. Options: mem, cpu, storage, storage_count, allocation

        // If provider_id and identity_id are not provided, defaults to using the selected provider/identity
        if (options.provider_id && options.identity_id) {
            this.provider_id = options.provider_id;
            this.identity_id = options.identity_id;
        }

	    Atmo.profile.bind('reset', this.render, this);
    },

    render: function() {

        var used = 0;        // Units of quota used
        var total = 0;        // Units of quota available
        var self = this;

        // First, determine which data we will use to create the charts -- selected provider, or data provided by AJAX calls
        if (this.provider_id && this.identity_id) {
            this.pull_cloud_data(this.provider_id, this.identity_id, this.quota_type);
        }
        else {
            total = Atmo.profile.get('selected_identity').get('quota')[this.quota_type];

            if (this.quota_type == 'storage') {
                $.each(Atmo.volumes.models, function(i, volume) {
                    used += parseInt(volume.get('size'));
                });
            }
            else if (this.quota_type == 'storage_count') {
                used = Atmo.volumes.models.length;
            }
            else if (this.quota_type == 'allocation') {
                if (! total) {
                    used = -1;
                    total = -1;
                } else {
                    quota_obj = total;
                    used = quota_obj['current']; //THIS IS A LIE!
                    total = quota_obj['threshold'];
                    alloc_obj = new Object();
                    alloc_obj.burn_time = quota_obj['burn'] //THIS IS ALSO A LIE! Damn.
                    alloc_obj.delta_time = quota_obj['delta']
                    // Make chart with our data and return
                    //TODO: true will instead be -1, 0, 1 to denote direction
                    this.make_chart(used, total, true, alloc_obj);
                    return this;
                }
            }
            else if (this.quota_type == 'cpu' || this.quota_type == 'mem') {

                if (Atmo.instance_types.models.length > 0) {
                    $.each(Atmo.instances.get_active_instances(), function(i, instance) {
                        var instance_type = instance.get('type');
                        var to_add = _.find(Atmo.instance_types.models, function(model) {
                            return model.attributes.alias == instance_type;
                        });
                        if (to_add)
                          used += to_add.get(self.quota_type);
                    });
                }
                else {
                    // Indicates error loading instance types
                    var info_holder = self.$el.parent().find('#' + self.quota_type + 'Holder_info');
                    var info = 'Could not calculate resource usage for ';
                    info += (self.quota_type == 'cpu') ? 'CPU usage' : 'memory usage';
                    info_holder.html(info);

                    // this.$el is the graph container
                    this.$el.addClass('graphBar');
                    this.$el.append('<div style="color: rgb(165, 42, 42); margin: 9px 10px 0px"><span>Unavailable</span></div>');
                    return this;
                }
            }

            // Make chart with our data
            this.make_chart(used, total, false);
        }
        
        return this;

    },
    pull_cloud_data: function(provider, identity, quota_type) {

        var total = 0, used = 0;
        var self = this;
        var fetch_errors = 0;

        // Get the quota, then get the quantity used
        $.ajax({
            type: 'GET',
            async: false,
            url: site_root + '/api/v1/provider/' + provider + '/identity/' + identity,
            success: function(response_text) {
                total = response_text[0]["quota"][quota_type];
            },
            error: function() {
                fetch_errors++;

                // Error Handling
                var info_holder = self.$el.parent().find('#' + quota_type + 'Holder_info');
                info_holder.html('Could not fetch ' + quota_type + ' quota. ');

                // this.$el is the graph container
                self.$el.addClass('graphBar');
                self.$el.append('<div style="color: rgb(165, 42, 42); margin: 9px 10px 0px"><span>Unavailable</span></div>');
            }
        });

        if (fetch_errors > 0) // Prevent unnecessary ajax calls if already in error state
            return;

        // Allocation Quota
        if (quota_type == 'allocation') {
            if (! total) {
                used = -1;
                total = -1;
            } else {
                used = total['current'];
                total = total['threshold'];
                // Make chart with our data
                self.make_chart(used, total, true);
                return self;
            }
        }
        // Volume-related Quotas
        else if (quota_type == 'storage' || quota_type == 'storage_count') {

            $.ajax({
                type: 'GET',
                url: site_root + '/api/v1/provider/' + provider + '/identity/' + identity + '/volume/',
                success: function(volumes) {

                    if (quota_type == 'storage') {
                        for (var i = 0; i < volumes.length; i++) {
                            used += parseInt(volumes[i].size);
                        }
                    }
                    else if (quota_type == 'storage_count') {
                        used = volumes.length;
                    }

                    // Make chart with our data
                    self.make_chart(used, total, false);
                },
                error: function() {
                    // Error handling
                    var info_holder = self.$el.parent().find('#' + quota_type + 'Holder_info');
                    var info = 'Could not fetch volume ';
                    info += (quota_type == 'storage') ? 'capacity quota.' : 'quantity quota.';
                    info_holder.html(info);

                    // this.$el is the graph container
                    self.$el.addClass('graphBar');
                    self.$el.append('<div style="color: rgb(165, 42, 42); margin: 9px 10px 0px"><span>Unavailable</span></div>');
                }

            });

        }
        // Instance-related Quotas
        else if (quota_type == 'mem' || quota_type == 'cpu') {

            var instances;

            // Get instances
            $.ajax({
                type: 'GET',
                async: false,
                url: site_root + '/api/v1/provider/' + provider + '/identity/' + identity + '/instance/',
                success: function(response_text) {
                    instances = response_text;
                },
                error: function() {
                    fetch_errors++;

                    // Error Handling
                    var info_holder = self.$el.parent().find('#' + quota_type + 'Holder_info');
                    var info = 'Could not fetch instance ';
                    info += (quota_type == 'mem') ? 'memory quota.' : 'CPU quota.';
                    info_holder.html(info);

                    // this.$el is the graph container
                    self.$el.addClass('graphBar');
                    self.$el.append('<div style="color: rgb(165, 42, 42); margin: 9px 10px 0px"><span>Unavailable</span></div>');
                }
            });

            if (fetch_errors > 0) // Prevent unnecessary ajax calls if already in error state
                return;

            // Get instance sizes
            $.ajax({
                type: 'GET',
                url: site_root + '/api/v1/provider/' + provider + '/identity/' + identity + '/size/',
                success: function(instance_types) {

                    // Filter out any instances that aren't active
                    instances = _.filter(instances, function(instance) {
                        return instance['state'] != 'suspended' && instances['state'] != 'shutoff';
                    });

                    // Add together quota used by instances cumulatively
                    for (var i = 0; i < instances.length; i++) {
                        var size_alias = instances[i].size_alias;
                        var to_add = _.filter(instance_types, function(type) {
                            return type.alias == size_alias;
                        });
                        used += to_add[0][quota_type];
                    }

                    if (quota_type == 'mem')
                        total *= 1024;

                    // Make chart with our data
                    self.make_chart(used, total, false);
                },
                error: function() {
                    // Error Handling
                    var info_holder = self.$el.parent().find('#' + quota_type + 'Holder_info');
                    info_holder.html('Could not fetch instance types. ');

                    // this.$el is the graph container
                    self.$el.addClass('graphBar');
                    self.$el.append('<div style="color: rgb(165, 42, 42); margin: 9px 10px 0px"><span>Unavailable</span></div>');
                }
            });
        }
    },
    choose_color: function(percent) {
        if (percent < 50)
            return 'greenGraphBar';
        else if (percent >= 50 && percent <= 100)
            return 'orangeGraphBar';
        else
            return 'redGraphBar';
    },
    make_usage_bar: function(percent, cssPercent, options) {

        // Style the usage bar
        var usage_bar = $('<div>', {
            style: 'width: 0%',
            html: function() {
                if (options && options.show_percent)
                    return '<span>' + percent + '%</span>';
                else
                    return '';
            }
        });

        if (options && options.show_color)
            usage_bar.addClass(this.choose_color(percent));

        if (cssPercent < 20)
            usage_bar.css('color', '#000');
        else
            usage_bar.css('color', '#FFF');

        return usage_bar;
    },
    make_chart: function(used, total, animate, time_obj) {

        // this.$el is the graph container
        this.$el.addClass('graphBar');

        var percent = 0, cssPercent = 0;

        if (used > 0) {
            percent = Math.min(100,Math.floor((used / total) * 100));
            cssPercent = (percent > 100) ? 100 : percent;
        }
        else {
            percent = 0;
            cssPercent = 0;
        }

        // Only create a new div element if one doesn't exist already that we can grow.
        var existing_bar = this.$el.find('[class$="GraphBar"]');

        // Slowly remove the added usage bar
        if (this.$el.find('.addedUsageBar').length > 0) {
            this.$el.find('.addedUsageBar').attr('class', '').addClass('addedUsageBar');
            this.$el.find('.addedUsageBar').addClass(this.choose_color(cssPercent));
            this.$el.find('.addedUsageBar').css('width', '0%');

            // Remove when bar has finished disappearing
            setTimeout(function() {
                $(existing_bar[0]).removeClass('barFlushLeft');
            }, 2 * 1000);
        }

        existing_bar = $(existing_bar[0]);
        var usage_bar;

        if (existing_bar.length == 0)
            usage_bar = this.make_usage_bar(percent, cssPercent, { show_percent: true, show_color: true });
        else {
            usage_bar = existing_bar;
            usage_bar.attr('class', '');
            usage_bar.addClass(this.choose_color(cssPercent));
            usage_bar.html('<span>' + percent + '%</span>');
        }

        usage_bar.css('width', '' + cssPercent + '%');
        if (animate) {
            usage_bar.addClass('active');
            usage_bar.addClass('positive-stripes');
        }

        if (usage_bar != existing_bar)
            this.$el.html(usage_bar);

        this.$el.data('used', used);
        this.$el.data('total', total);
        var total_usage = Math.floor(( this.$el.data('used') / this.$el.data('total')) * 100);
        var under_quota = (total_usage > 100) ? false : true;
        this.show_quota_info(used, total, false, under_quota, time_obj);
    },
    /**
     * Populates the informational field below the graph to tell the user exactly what their resource usage is.
     */
    show_quota_info: function(used, total, is_projected, under_quota, time_obj) {
        // is_projected: boolean, should quota denote future use or current use

        var info = '',
            selected_identity = Atmo.profile.get('selected_identity'),
            quota = selected_identity.get('quota'),
            time_quota_left,
            end_date;
        if (quota.allocation !== null && quota.allocation !== undefined) {
            time_quota_left = quota.allocation.ttz,
            end_date = time_quota_left ? new Date(time_quota_left) : null;
        } 
        
        if (this.quota_type == 'cpu') {
            quota_title = "Processor Unit";
            quota_desc = "aproximation of CPU hours";
            quota_unit = "CPU";
            this.$el.data('unit', 'CPUs');
        }
        else if (this.quota_type == 'mem') {
            quota_title = "Memory";
            quota_desc = "total amount of memory";
            quota_unit = "GB";

            // Determine whether memory should be in GB or MB
            this.$el.data('unit', 'memory');
            used = (used / 1024).toFixed(0);
            total = (total / 1024).toFixed(0);
        }
        else if (this.quota_type == 'storage') {
            quota_title = "Disk Space";
            quota_desc = "total amount of storage";
            quota_unit = "GB";
            this.$el.data('unit', 'storage');
        }
        else if (this.quota_type == 'storage_count') {
            quota_title = "Storage Count";
            quota_desc = "total number of volumes";
            quota_unit = "volume";
            this.$el.data('unit', 'volumes');
        }
        else if (this.quota_type == 'allocation') {
            quota_title = "Time";
            d = new Date();
            d.setTime(d.getTime() - (time_obj.delta_time * 60 * 1000)) // ms to minutes
            quota_desc = "total number of Atmosphere Units used since "+d.toString('MMMM dS, yyyy');
            quota_unit = "AU";
            this.$el.data('unit', 'AU');
        }
        info = used + ' of ' + total + ' allotted ' + quota_unit + 's.';

        if (is_projected)
            info = 'You will use ' + info;
        else
            info = 'You are using ' + info;
        if (used == -1 && total == -1) {
            info = 'Running time is not being counted on this provider.';
        }

        if (!under_quota) {
            info = '<strong>Quota Exceeded.</strong> ';

            if (this.quota_type == 'mem' || this.quota_type == 'cpu')
                info += 'Choose a smaller size or terminate a running instance.';
            else if (this.quota_type == 'storage')
                info += 'Choose a smaller size or destroy an existing volume.';
            else if (this.quota_type == 'storage_count')
                info += 'You must destroy an existing volume or request more resources.';
            else if (this.quota_type == 'allocation')
                info += 'You must request more allocation or wait until your running time is below 100% to resume your instances or create new instances.';
        }

        // Place info into sibling div element
        var info_holder = this.$el.parent().find('#' + this.quota_type + 'Holder_info');
        info_holder.html(info);
        var remaining = Math.max(0,total - used);
        var remaining_str = remaining + ' ' + quota_unit + 's';

        popover_content = 'The graph above represents the <b>' + quota_desc + ' you have currently used</b> for this provider.<br /><br />';
        popover_content += 'As of now, you have <b>' +  remaining_str + ' remaining.</b><br /><br />';
        if (time_obj != null && time_obj.burn_time != null && end_date) {
            popover_content += "Given your current instance configuration, you will <b>run out of ALL your instance time by  " +
            ((end_date != undefined) ? end_date._toString() : remaining_str) +'</b>';
        }
        this.$el.popover('destroy');
        this.$el.popover({
            placement: 'bottom',
            delay: {'hide':400},
            trigger: 'hover',
            title: quota_title + ' Allocation <a class="close" data-dismiss="popover" href="#new_instance" data-parent="help_image">&times</a>',
            html: true,
            content: popover_content,
        });


    },
    /**
     * Adds predicted usage to user's resource charts and determines whether or not the user would be under quota.
     */
    add_usage: function(to_add, options) {

        var under_quota;

        var info_holder = this.$el.parent().find('#' + this.quota_type + 'Holder_info');
        to_add = parseFloat(to_add);

        // Empty the existing parts
        //this.$el.html('');

        var new_usage = Math.round((to_add / this.$el.data('total')) * 100);
        var current_usage = Math.floor((this.$el.data('used') / this.$el.data('total')) * 100);
        var total_usage = Math.floor(((to_add + this.$el.data('used')) / this.$el.data('total')) * 100);
        var new_cssPercent = 0;

        var under_quota = (total_usage > 100) ? false : true;

        // Create new usage bars
        if (current_usage > 0 && current_usage < 100) {

            // Determine the size of the added part
            if (total_usage > 100)
                new_cssPercent = 100 - current_usage;
            else
                new_cssPercent = new_usage;

            var current_bar = this.$el.find('[class$="GraphBar"]');
            current_bar = $(current_bar[0]);

            if (current_bar.length == 0)
                var current_bar = this.make_usage_bar(current_usage, current_usage, { show_percent: false, show_color: false });

            current_bar.html('<span>' + total_usage + '%</span>');
            current_bar.attr('class', '');
            current_bar.addClass('barFlushLeft');
            current_bar.addClass(this.choose_color(total_usage));

            var added_bar = this.$el.find('.addedUsageBar');
            added_bar = $(added_bar[0]);

            if (added_bar.length == 0)
                added_bar = this.make_usage_bar(new_usage, new_cssPercent, { show_percent: false, show_color: false });

            added_bar.attr('class', '');
            added_bar.addClass(this.choose_color(total_usage));
            added_bar.css('opacity', 0.5);
            added_bar.addClass('addedUsageBar');

            // Only append if they didn't exist before
            if (this.$el.find('.addedUsageBar').length == 0) {
                this.$el.append(added_bar);
                setTimeout(function() {
                    current_bar.css('width', '' + current_usage + '%');
                    added_bar.css('width', '' + new_cssPercent + '%');
                }, 0.5 * 1000);
            }
            else {
                current_bar.css('width', '' + current_usage + '%');
                added_bar.css('width', '' + new_cssPercent + '%');
            }
        }
        else {

            // User is already over quota
            if (total_usage > 100)
                new_cssPercent = 100;
            else
                new_cssPercent = new_usage;

            var added_bar = this.make_usage_bar(total_usage, new_cssPercent, { show_percent: true, show_color: true });
            added_bar.css('opacity', 0.5);
            added_bar.css('color', '#000');
            this.$el.html(added_bar);
            added_bar.css('width', '' + new_cssPercent + '%');
        }

        this.show_quota_info((this.$el.data('used') + to_add), this.$el.data('total'), true, under_quota);

        // Return: whether the user is under their quota with the added usage
        return under_quota;

    },
    /* Only used when user is resizing instance to a smaller size */
    sub_usage: function(to_sub, options) {

        var under_quota;

        var info_holder = this.$el.parent().find('#' + this.quota_type + 'Holder_info');
        to_sub = parseFloat(to_sub);

        // Empty the existing parts
        //this.$el.html('');

        var current_usage = Math.floor((to_sub / this.$el.data('total')) * 100);
        var projected_usage = Math.floor((this.$el.data('used') / this.$el.data('total')) * 100) - current_usage;
        var total_usage = Math.floor(((this.$el.data('used') - to_sub) / this.$el.data('total')) * 100);

        // Create new usage bars -- only if necessary, though
        var projected_bar;
        var existing_projected = this.$el.find('[class$="GraphBar"]');
        existing_projected = $(existing_projected[0]);

        if (existing_projected.length == 0)
            projected_bar = this.make_usage_bar(projected_usage, projected_usage, { show_percent: false, show_color: false });
        else
            projected_bar = existing_projected;

        projected_bar.html('<span>' + total_usage + '%</span>');
        projected_bar.attr('class', '');
        projected_bar.addClass('barFlushLeft');
        projected_bar.addClass(this.choose_color(total_usage));

        // Create current bar -- only if necessary
        var existing_current = this.$el.find('.addedUsageBar')[0];
        existing_current = $(existing_current);

        if (existing_current.length == 0)
            current_bar = this.make_usage_bar(current_usage, current_usage, { show_percent: false, show_color: false });
        else
            current_bar = existing_current;

        current_bar.attr('class', '');
        current_bar.addClass(this.choose_color(total_usage));

        // If you're not subtracting any usage, make up for the fact that projected bar will be 0%
        if (to_sub > 0) {
            current_bar.css('opacity', 0.5);
            current_bar.addClass('addedUsageBar');
        }
        else {
            projected_bar.removeClass('barFlushLeft');
        }

        if (to_sub > 0 && projected_usage == 0) {
            current_bar.html('<span>' + total_usage + '%</span>');
            projected_bar.html('');
        }

        if (projected_bar != existing_projected)
            this.$el.html(projected_bar);
        if (current_bar != existing_current)
            this.$el.html(projected_bar).append(current_bar);

        //if (projected_bar == existing_projected && current_bar == existing_current) {
            projected_bar.css('width', '' + projected_usage + '%');
            current_bar.css('width', '' + current_usage + '%');
        //}
        //else {
        //    setTimeout(function() {
        //        projected_bar.css('width', '' + projected_usage + '%');
        //        current_bar.css('width', '' + current_usage + '%');
        //    }, 1.5 * 1000);
        //}

        this.show_quota_info((this.$el.data('used') - to_sub), this.$el.data('total'), true, true);

        // When a user is resizing an instance lower, they will always be under quota
        return true;
    }
});
