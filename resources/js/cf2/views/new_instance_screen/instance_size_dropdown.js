Atmo.Views.InstanceSizeDropdown = Backbone.View.extend({
    tagName: "select",
    id: "newinst_size",
    events: {
		'change': 'change_type_selection',
    },
    initialize: function(options) {
		Atmo.instance_types.bind('reset', this.render, this);
    },
	change_type_selection: function(e) {
		$(e.currentTarget).find(':selected').data('instance_type').select();
	},
    render: function() {
		if (Atmo.instance_types.models.length <= 0) {
            this.no_size_information();
            return this;
        }

        var self = this;
        Atmo.instance_types.each(function(model) {
            self.$el.append(self.type_option(model));
        });

        // Sets initial selected_instance_type to m1.small
        var default_instance = Atmo.profile.attributes['settings'].default_size;
        this.$el
            .val(default_instance)
            .trigger('change');
        return this;
    },
    no_size_information: function() {
        // Error getting instance types for this provider, inform user.
        //this.launch_lock = true;
        this.$el
            .append($('<option>', {
                html: 'Instance Sizes Unavailable', 
                disabled: 'disabled'
            }))
            .closest('.control-group').addClass('error')
            .parent()
                .find('.help-block').remove().end()
                .append($('<div/>', {
                    'class': 'help-block',
                    html: 'If this problem persists, please contact Support.'
                }));
    },
    type_option: function(instance_type) {
        if (instance_type.get('active') == false)
            return;
        var opt = $('<option>', {
            value: instance_type.get('id'),
            html: function() {
                // Determine how many digits we want to display
                var digits = (instance_type.get('mem') % 1024 == 0) ? 0 : 1;

                // Make a human readable number
                var mem = (instance_type.get('mem') > 1024) ? '' + (instance_type.get('mem') / 1024).toFixed(digits) + ' GB' : (instance_type.get('mem') + ' MB') ;
                return instance_type.get('name') + ' (' + instance_type.get('cpus') + ' CPUs, ' + mem + ' memory, ' + instance_type.get('disk') + ' GB disk)';
            },
            'data' : {'instance_type' : instance_type}
        });

        if (instance_type.get('remaining') > 0) {
            opt.data('available', true);
        } else {
            opt.data('available', false);
            opt.attr('disabled', 'disabled');
            opt.html(opt.html() + ' (At Capacity)');
        }
        return opt;
    }
});
