Atmo.Views.HypervisorDropdown = Backbone.View.extend({
    tagName: "select",
    id: "newinst_hypervisor",
    events: {
		'change': 'change_hypervisor_selection',
    },
    initialize: function(options) {
	    Atmo.instance_hypervisors.bind('reset', this.render, this);
    },
	change_hypervisor_selection: function(e) {
		$(e.currentTarget).find(':selected').data('instance_hypervisor').select();
	},
    render: function() {
        var instance_hypervisors = Atmo.instance_hypervisors,
            self = this,
            hypervisor_option,
            default_instance;

	if (!instance_hypervisors.models.length) {
            this.no_hypervisor_information();
        } else {
            //There is a hypervisor list for this provider...
            //Add one 'blank' so a node is not auto-selected.
            //and default behavior is to auto-schedule
            var blank_opt = $('<option>', {
                value: "",
                html: function() {
                    // Determine how we display the hypervisor
                    return "Auto-select hypervisor";
                },
                'data' : {'instance_hypervisor' : ''},
            });
            blank_opt.data('available', true);
            self.$el.append(blank_opt);
            instance_hypervisors.each(function (model) {
                option_obj = self.hypervisor_option(model);
                if (option_obj != undefined) {
                    self.$el.append(option_obj);
                }
            });
        }
        return this;
    },
    no_hypervisor_information: function() {
        // Error getting hypervisors for this provider, inform user.
        //this.launch_lock = true;
        this.$el
            .append($('<option>', {
                html: 'No hypervisors found.',
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
    hypervisor_option: function(instance_hypervisor) {
        var opt = $('<option>', {
            value: instance_hypervisor.get('service_region')+':'+instance_hypervisor.get('name'),
            html: function() {
                // Determine how we display the hypervisor
                return instance_hypervisor.get('name') ;
            },
            'data' : {'instance_hypervisor' : instance_hypervisor},
        });
        opt.data('available', true);
        return opt;
    }
});
