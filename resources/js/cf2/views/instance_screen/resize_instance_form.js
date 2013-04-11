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
		'change select[name="new_instance_size"]' : 'select_instance_size',
		'submit form' : 'resize_instance'
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
				if (self.model.get('size_alias') == instance_type.get('alias')) {
					opt.attr('selected', 'selected');	
				}

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

		var self = this;
		var new_instance_type = this.$el.find('select[name="new_instance_size"] :selected').data('instance_type');

		var new_size = parseInt(new_instance_type.get('alias'));
		var old_size = parseInt(this.model.get('size_alias'));

		if (new_size == old_size) {
			this.mem_resource_chart.render();
			this.cpu_resource_chart.render();
		}
		else if (new_size > old_size) {
			var under_mem = this.mem_resource_chart.add_usage(new_instance_type.get('mem'));
			var under_cpu = this.cpu_resource_chart.add_usage(new_instance_type.get('cpu'));

			if (under_mem && under_cpu)
				this.$el.find('input[type="submit"]').removeAttr('disabled');
			else
				this.$el.find('input[type="submit"]').attr('disabled', 'disabled');
		}
		else if (new_size < old_size) {

			this.$el.find('input[type="submit"]').removeAttr('disabled');

			var old_type = _.filter(Atmo.instance_types.models, function(type) {
				return type.get('alias') == self.model.get('size_alias');
			});
			var old_instance_type = old_type[0];

			var sub_mem = old_instance_type.get('mem') - new_instance_type.get('mem');
			var sub_cpu = old_instance_type.get('cpu') - new_instance_type.get('cpu');

			this.mem_resource_chart.sub_usage(sub_mem);
			this.cpu_resource_chart.sub_usage(sub_cpu);
		}

		console.log(this.$el.closest('.instance_tabs_holder'));

	},
	resize_instance: function(e) {

		e.preventDefault();

		var id = Atmo.profile.get('selected_identity');
		var self = this;
		var size_alias = this.$el.find('select[name="new_instance_size"] :selected').data('instance_type').get('alias');
		var data = { 'action' : 'resize',
					 'size' : size_alias };

		// Don't allow user to resize to same size
		if (size_alias == this.model.get('size_alias')) {
			Atmo.Utils.notify('No size change', 'Select a different size to resize your instance.');
			return false;
		}
			
		this.$el.find('input[type="submit"]').attr('disabled', 'disabled').val('Resizing Instance...');

		$.ajax({
			url: site_root + '/api/provider/' + id.get('provider_id') + '/identity/' + id.get('id') + '/instance/' + self.model.get('id') + '/action/',
			type: 'POST',
			data: data,
			success: function() {
				Atmo.Utils.notify('Resizing Instance', 'Instance will finish resizing shortly.');

				// Merges models to those that are accurate based on server response
				Atmo.instances.update();
				this.$el.find('input[type="submit"]').removeAttr('disabled').val('Resize Instance');
			},
			error: function() {
				Atmo.Utils.notify(
					'Could not resize instance', 
					'If the problem persists, please contact <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', 
					{ no_timeout: true }
				);
			}
		});
	},
	instance_type_fail: function() {
		
	}
});
