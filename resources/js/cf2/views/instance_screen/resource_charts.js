Atmo.Views.ResourceCharts = Backbone.View.extend({
	initialize: function(options) {

		// Options: quota_type, provider_id, identity_id

		this.quota_type = options.quota_type;

		if (options.provider_id && options.identity_id) {
			this.provider_id = options.provider_id;
			this.identity_id = options.identity_id;
		}
	},
	render: function() {

		// First, determine which data we will use to create the charts
		var used = 0, total = 0, self = this;

		// Do ajax calls to get data
		if (this.provider_id && this.identity_id) {
			this.pull_cloud_data(this.provider_id, this.identity_id, this.quota_type);
		}
		else {
			total = Atmo.profile.get('selected_identity').get('quota')[this.quota_type];

			if (this.quota_type == 'disk') {
				$.each(Atmo.volumes.models, function(i, volume) {
					used += parseInt(volume.get('size'));
				});
			}
			else if (this.quota_type == 'disk_count') {
				used = Atmo.volumes.models.length;
			}
			else if (this.quota_type == 'cpu' || this.quota_type == 'mem') {

				if (Atmo.instance_types.models.length > 0) {
					$.each(Atmo.instances.models, function(i, instance) {
						var instance_type = instance.get('type');
						var to_add = _.filter(Atmo.instance_types.models, function(model) {
							return model.attributes.alias == instance_type;
						});
						used += to_add[0].attributes[self.quota_type];
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
			this.make_chart(used, total);
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
			url: site_root + '/api/provider/' + provider + '/identity/' + identity,
			success: function(response_text) {
				console.log("total", total);
				total = response_text["quota"][quota_type];
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

		// Volume-related Quotas
		if (quota_type == 'disk' || quota_type == 'disk_count') {

			$.ajax({
				type: 'GET',
				url: site_root + '/api/provider/' + provider + '/identity/' + identity + '/volume/',
				success: function(volumes) {

					if (quota_type == 'disk') {
						for (var i = 0; i < volumes.length; i++) {
							used += parseInt(volumes[i].size);
						}
					}
					else if (quota_type == 'disk_count') {
						used = volumes.length;
					}

					// Make chart with our data
					self.make_chart(used, total);
				},
				error: function() {
					// Error handling
					var info_holder = self.$el.parent().find('#' + quota_type + 'Holder_info');
					var info = 'Could not fetch volume ';
					info += (quota_type == 'disk') ? 'capacity quota.' : 'quantity quota.';
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
				url: site_root + '/api/provider/' + provider + '/identity/' + identity + '/instance/',
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
				url: site_root + '/api/provider/' + provider + '/identity/' + identity + '/size/',
				success: function(instance_types) {


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
					self.make_chart(used, total);
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
			style: 'width: ' + cssPercent + '%',
			html: function() {
				if (options && options.show_percent)
					return '<span>' + percent + '%</span>';
				else
					return '';
			}
		});
		
		if (options && options.show_color)
			usage_bar.addClass(this.choose_color(percent));
		
		if (usage_bar.width() < 10)
			usage_bar.css('color', '#000');
		else
			usage_bar.css('color', '#FFF');

		return usage_bar;
	},
	make_chart: function(used, total) {
		
		// this.$el is the graph container
		this.$el.addClass('graphBar');

		var percent = 0, cssPercent = 0;

		if (used > 0) {
			percent = Math.floor((used / total) * 100);
			cssPercent = (percent > 100) ? 100 : percent;
		}
		else {
			percent = 0;
			cssPercent = 0;
		}
		var usage_bar = this.make_usage_bar(percent, cssPercent, { show_percent: true, show_color: true });

		this.$el.html(usage_bar);
		this.$el.data('used', used);
		this.$el.data('total', total);

		this.show_quota_info(used, total, false, true);
	},
	show_quota_info: function(used, total, is_projected, under_quota) {
		// is_projected: boolean, should quota denote future use or current use
		
		var info = '';

		if (this.quota_type == 'cpu') {
			this.$el.data('unit', 'CPUs');
			info = used + ' of ' + total + ' available CPUs.';
		}
		else if (this.quota_type == 'mem') {

			// Determine whether memory should be in GB or MB
			this.$el.data('unit', 'memory');
			var digits = (used % 1024 == 0) ? 0 : 1;
			var readable_used = (used > 1024) ? ('' + (used / 1024).toFixed(digits) + ' GB') : ('' + used + ' MB');

			info = readable_used + ' of ' + (total / 1024) + ' GB allotted memory.';
		}
		else if (this.quota_type == 'disk') {
			this.$el.data('unit', 'storage');
			info = used + ' of ' + total + ' GB available storage.';
		}
		else if (this.quota_type == 'disk_count') {
			this.$el.data('unit', 'volumes');
			info = used + ' of ' + total + ' available volumes.';
		}

		if (is_projected)
			info = 'You will use ' + info;
		else
			info = 'You are using ' + info;

		if (!under_quota) {
			info = '<strong>Quota Exceeded.</strong> ';

			if (this.quota_type == 'mem' || this.quota_type == 'cpu')
				info += 'Choose a smaller size or terminate a running instance.';
			else if (this.quota_type == 'disk')
				info += 'Choose a smaller size or destroy an existing volume.';
			else if (this.quota_type == 'disk_count')
				info += 'You must destroy an existing volume or request more resources.';
		}

		// Place info into sibling div element
		var info_holder = this.$el.parent().find('#' + this.quota_type + 'Holder_info');
		info_holder.html(info);

	},
	add_usage: function(to_add, options) {
		
		var under_quota;

		var info_holder = this.$el.parent().find('#' + this.quota_type + 'Holder_info');
		to_add = parseFloat(to_add);

		// Empty the existing parts
		this.$el.html('');	

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

			var current_bar = this.make_usage_bar(current_usage, current_usage, { show_percent: false, show_color: false });
			current_bar.html('<span>' + total_usage + '%</span>');
			current_bar.attr('class', '');
			current_bar.addClass('barFlushLeft');
			current_bar.addClass(this.choose_color(total_usage));

			var added_bar = this.make_usage_bar(new_usage, new_cssPercent, { show_percent: false, show_color: false });
			added_bar.addClass(this.choose_color(total_usage));
			added_bar.css('opacity', 0.5);
			added_bar.addClass('addedUsageBar');

			this.$el.html(current_bar).append(added_bar);
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
		}

		this.show_quota_info((this.$el.data('used') + to_add), this.$el.data('total'), true, under_quota);

		// Return: whether the user is under their quota with the added usage
		return under_quota;

	}
});
