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
		this.$el.data('instance', this.model);
		this.model.bind('change', this.render, this);
		this.model.bind('change:running_shell', this.update_running_state, this);
		this.model.bind('change:running_vnc', this.update_running_state, this);
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
			if (this.$el.find('.bd b').html() != this.model.get('name_or_id')) {
				this.$el.find('.bd b').html(this.model.get('name_or_id'));
			}

			// Update IP address, if needed
			if (this.$el.find('.bd span').html() != this.model.get('public_dns_name')) {
				this.$el.find('.bd span').html(this.model.get('public_dns_name'));
			}
			
			// Update running state if needed
			this.$el.find('.instance_state').attr('class', 'instance_state');
			this.$el.find('.instance_state').html('Instance is ' + this.model.get('state'));
		}

		if (this.model.get('selected'))
			this.$el.addClass('active');
		this.update_running_state();

		// Use the provider generic states: 'active', 'build', 'delete'
		this.$el.find('.instance_state').addClass(function() {
			var states = ['active', 'build', 'delete'];
			for (var i = 0; i < states.length; i++) {
				if (self.model.get('state_is_'+states[i]))
					return 'instance_state_is_' + states[i];
			}
			return 'instance_state_is_delete';		// If none of the instance states are true, assume it's an error
		});

		setTimeout(function() {
			self.$el.find('div').slideDown();
		}, 1500);

		this.rendered = true;

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
            Atmo.Utils.notify("Please wait", "Instance is already " + this.model.get('state') + ".");
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
					Atmo.Utils.notify("Could not delete this volume", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
				},
            });
        }
	}
});
