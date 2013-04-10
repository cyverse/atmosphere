/**
 *
 * Resizes an instance and validates the resize based on a user's quota.
 *
 */
Atmo.Views.ResizeInstanceForm = Backbone.View.extend({
	'tagName': 'div',
    'className': 'resize_instance_form',
	template: _.template(Atmo.Templates.resize_instance_form),
	initialize: function() {
		Atmo.instance_types.bind('reset', this.render_instance_type_list, this);
		Atmo.instance_types.bind('fail', this.instance_type_fail, this);
	},
	events: {
		'change select[name="new_instance_size"]' : 'select_instance_size'
	},
	render: function() {
		this.$el.html(this.template(this.model.toJSON()));
		
		this.mem_resource_chart = new Atmo.Views.ResourceCharts({
			el: this.$el.find('#memHolder'), 
			quota_type: 'mem',
		}).render();
		this.cpu_resource_chart = new Atmo.Views.ResourceCharts({
			el: this.$el.find('#cpuHolder'), 
			quota_type: 'cpu'
		}).render();

		this.render_instance_type_list();

		// Keep track of whether user is under quota
		this.under_quota = true;

		return this;
    },
	render_instance_type_list: function() {
		if (Atmo.instance_types.models.length > 0) {

			this.$el.find('select[name="new_instance_size"]').empty();

			var set_default = false;
			this.under_quota = false;

			var self = this;
			$.each(Atmo.instance_types.models, function(i, instance_type) {
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
	select_instance_size: function() {
		var instance_type = this.$el.find('select[name="new_instance_size"] :selected').data('instance_type');


	},
	instance_type_fail: function() {
		
	}
});
