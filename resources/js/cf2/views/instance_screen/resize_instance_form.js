Atmo.Views.ResizeInstanceForm = Backbone.View.extend({
	'tagName': 'div',
    'className': 'resize_instance_form',
	template: _.template(Atmo.Templates.resize_instance_form),
	initialize: function() {
		Atmo.instance_types.bind('reset', this.render_instance_type_list, this);
		Atmo.instance_types.bind('fail', this.instance_type_fail, this);
	},
	render: function() {
		this.$el.html(this.template(this.model.toJSON()));
		
		this.render_instance_type_list();

		// Keep track of whether user is under quota
		this.under_quota = true;

		return this;
    },
	render_instance_type_list: function() {
		console.log("render_instance_type_list", Atmo.instance_types.models.length);
		if (Atmo.instance_types.models.length > 0) {

			this.$el.find('select[name="new_instance_size"]').empty();

			var set_default = false;
			this.under_quota = false;

			var self = this;
			$.each(Atmo.instance_types.models, function(idx, instance_type) {
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

				// Start the user off at the size their instance currently is.
				if (self.model.get('size_alias') == instance_type.get('name'))
					opt.attr('selected', 'selected');	

				if (instance_type.get('remaining') > 0) {
					opt.data('available', true);
					/*if (!set_default) {
						var enough_cpus = self.cpu_resource_chart.add_usage(instance_type.attributes.cpus, "cpuHolder");
						var enough_mem = self.mem_resource_chart.add_usage(instance_type.attributes.mem, "memHolder");
						if (enough_cpus && enough_mem) {
							self.under_quota = true;
						}
						else {
							self.$el.find('#launchInstance').attr('disabled', 'disabled');
							self.under_quota = false;
						}
						set_default = true;
					}*/
				}
				else {
					opt.data('available', false);
					opt.attr('disabled', 'disabled');
					opt.html(opt.html() + ' (At Capacity)');
				}
				self.$el.find('select[name="new_instance_size"]').append(opt);
			});

            this.$el.find('select[name="new_instance_size"]').trigger('change');
		}

	},
	instance_type_fail: function() {
		
	}
});
