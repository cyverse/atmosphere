/* Bar charts that show cpu and memory usage */
Atmo.Views.ResourceCharts = Backbone.View.extend({
	initialize: function(options) {
		this.quota_type = options.quota_type;

        // Get quota for any provider and id, but assume selected_identity otherwise 
        if (options.provider && options.identity_id) {
            this.provider = options.provider;
            this.identity_id = options.identity_id;
        }

	},
	render: function() {
		
		var self = this;
		total = Atmo.profile.get('selected_identity').get('quota')[self.quota_type];
		used = 0;

        // If we're given a 'provider' and 'identity_id' as args, use those. Otherwise, compute based on selected identity

		var fetch_errors = 0;
		
        if (!this.provider && !this.identity_id) {
            if (this.quota_type == 'disk') {
                
                $.each(Atmo.volumes.models, function(i, volume) {
                    used += parseInt(volume.get('size'));
                });

            }
			else if (this.quota_type == 'disk_count') {
				used = Atmo.volumes.models.length;
			}
            else if (this.quota_type == 'cpu' || this.quota_type == 'mem') {

					// First, check for stuff that would break this.
					if (Atmo.instance_types.models.length == 0) {
						fetch_errors++;
						$('#instances_' + self.identity_id).html('<div class="alert alert-error"><strong>Could not get instance sizes for this provider.</strong> If the problem persists, please contact Support.</div>');

						// Don't let people launch as a result of a size fetch error
						used = total;

						if (this.$el.attr('id') == "cpuHolder") {
							this.$el.parent().find('#cpuHolder_info').html('<div class="alert alert-error"><strong>Error</strong> Could not calcuate your CPU usage. Contact Support.</div>');
						}
						else if (this.$el.attr('id') == "memHolder") {
							this.$el.parent().find('#memHolder_info').html('<div class="alert alert-error"><strong>Error</strong> Could not calcuate your memory usage. Contact Support.</div>');
						}
					}
					else {
						$.each(Atmo.instances.models, function(idx,instance) {

							var instance_type = instance.get('type');
							var to_add = _.filter(Atmo.instance_types.models, function(model) {
								return model.attributes.alias == instance_type;
							});
							used += to_add[0].attributes[self.quota_type];

						});
					}

            }
			this.fetch_errors = fetch_errors;
            this.make_chart(used, total);
        }
        else {
            // Get the user's quota for given identity, query for for that quota_type and add together the sizes

            this.total = 0;
            this.used = 0;


            $.ajax({
                type: 'GET',
                url: site_root + '/api/provider/' + self.provider + '/identity/' + self.identity_id,
                success: function(response_text) {

                    // Get quota requested
                    self.total = response_text.quota[self.quota_type];

                    if (self.quota_type == 'disk' || self.quota_type == 'disk_count') {
                        // Get only volumes

                        $.ajax({
                            type: 'GET',
                            url: site_root + '/api/provider/' + self.provider + '/identity/' + self.identity_id + '/volume/', 
                            success: function(response_text) {
                                self.volumes = response_text;

								if (self.quota_type == 'disk') {
									for (var i = 0; i < self.volumes.length; i++) {
										self.used += parseInt(self.volumes[i].size);
									}
								}
								else {
									self.used = self.volumes.length;
								}

                                // MAKE CHART
                                self.make_chart(self.used, self.total);

                            },
							error: function() {
								$('#volumes_' + self.identity_id).html('<div class="alert alert-error"><strong>Could not get volumes for this provider.</strong> If the problem persists, please contact Support.</div>');

								fetch_errors++;
							},
                            dataType: 'json'
                        });
                    }
                    else {
                        // Make a list of the instance types being used

                        $.ajax({
                            type: 'GET',
                            async: false,           // We have to wait for this to finish to proceed anyways
                            url: site_root + '/api/provider/' + self.provider + '/identity/' + self.identity_id + '/instance/', 
                            success: function(response_text) {
                                self.instances = response_text;
                            },
							error: function() {
								$('#instances_' + self.identity_id).html('<div class="alert alert-error"><strong>Could not get instances for this provider.</strong> If the problem persists, please contact Support.</div>');
								fetch_errors++;
							},
                            dataType: 'json'
                        });
                        $.ajax({
                            type: 'GET',
                            url: site_root + '/api/provider/' + self.provider + '/identity/' + self.identity_id + '/size/', 
                            success: function(response_text) {
                                // Get provider sizes and calculate used
                                self.instance_types = response_text;

                                // Go through instances, add based on quota type and alias
                                for (var i = 0; i < self.instances.length; i++) {
                                    var size_alias = self.instances[i].size_alias;
                                    var to_add = _.filter(self.instance_types, function(type) {
                                        return type.alias == size_alias;
                                    });
                                    self.used += to_add[0][self.quota_type];
                                    
                                }

								if (self.quota_type == 'mem') {
									self.total *= 1024;
								}

                                // MAKE CHART
                                self.make_chart(self.used, self.total);

                            },
							error: function() {
								fetch_errors++;

								$('#resource_usage_holder_iplant_' + self.identity_id  + ' #cpuHolder_info').html('<div class="alert alert-error"><strong>Could not build resource usage charts.</strong> If the problem persists, please contact Support.</div>');

								// Last call -- if errors occured, alert user.
								if (fetch_errors > 0) {
									Atmo.Utils.notify("Error", 'Could not find all information for this cloud. If the problem persists, please use the "Feedback &amp; Support" button in the lower right or email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
								}
							},
                            dataType: 'json'
                        });
                    }
                },
				error: function() {
					fetch_errors++;
				},
                dataType: 'json'
            });


        }


		return this;
	},
	choose_color: function(percent) {

		if (percent < 50) {
			return "greenGraphBar";	
		}
		else if (percent >= 50 && percent < 80) {
			return "orangeGraphBar";
		}
		else {
			return "redGraphBar";
		}

	},
	make_fill: function(percent) {

		var self = this;

		var cssPercent = percent * 100;
        if (cssPercent > 100) cssPercent = 100;

		var el = $('<div/>', {
			style: 'width: ' + Math.round(cssPercent) + '%'
		});

		var barColor = this.choose_color(cssPercent);
		el.addClass(barColor);

		if (!this.fetch_errors)
			el.html('<span>' + Math.round(percent * 100) + '%</span>');
		else
			el.html('<span>Unavailable</span>');

        // Keep the percentage 
        if (el.width() < 10) 
            el.css('color', '#000');
        else
            el.css('color', '#FFF');

		return el;
	},
	make_chart: function(part, whole) {

		var bar = this.$el;
		bar.addClass("graphBar");

		if (whole < 0) whole = part;

		// Only draw fill bars if their usage is > 0
		if (part != 0) {

			// Create the bar that will go inside
			var percent = part / whole;

			var fill = this.make_fill(percent);
			
			bar.html(fill);
		}
		else {
			var percent = 0;
			var fill = this.make_fill(percent);
			bar.html(fill);
		}

		// Store this so you can call add_usage with just the extra resource usage
		bar.data("whole", whole);
		bar.data("part", part);

		// In the case of the cpu and memory holders, want to include actual usage
		// in numbers

		if (this.$el.attr('id') == "cpuHolder" && !this.fetch_errors) {
			bar.data("unit", "CPUs");
			this.$el.parent().find('#cpuHolder_info').html("You are using " + part + " of " + whole + " CPUs");
		}
		else if (this.$el.attr('id') == "memHolder" && !this.fetch_errors) {
			bar.data("unit", "GB available memory");
			// Display member in GB or MB when appropriate
			// Determine how many digits we want to display

			var digits = (part % 1024 == 0) ? 0 : 1;
			readable_part = (part > 1024) ? ('' + (part/1024).toFixed(digits)  + ' GB') : ('' + part + ' MB');

			this.$el.parent().find('#memHolder_info').html("You are using " + readable_part + " of " + (whole/1024) + " GB  available memory.");
		}
		else if (this.$el.attr('id') == 'diskHolder' && !this.fetch_errors) {
			bar.data("unit", "GB available storage");
			this.$el.parent().find('#diskHolder_info').html('You are using ' + part + ' of ' + whole + ' GB available storage.');
		}
		else if (this.$el.attr('id') == 'disk_countHolder' && !this.fetch_errors) {
			bar.data("unit", "available volumes");
			this.$el.parent().find('#disk_countHolder_info').html('You are using ' + part + ' of ' + whole + ' available volumes.');
		}

		if (part > 0) {
			bar.append($('<br/>', {
				style: 'clear: both'
			}));
		}

	},
	add_usage: function(extraPart, options) {
		var self = this;

		if (options)
			this.is_initial = options.is_initial;

		var chart = this.$el;
		var chart_info = this.$el.parent().find('#'+self.quota_type+"Holder_info");
		extraPart = parseFloat(extraPart);

		var fill = chart.html();
		fill = $(fill);


		// Erase any "extra" already added in
		if (fill.length != 0) {
			if (chart.data("part") == 0) {
				fill = "";

				chart.append($('<br/>', {
					style: 'clear: both'
				}));
			}
			else {
				fill = $(fill[0]);
			}
			chart.html(fill);
		}

		var cssPercent = Math.round((extraPart / chart.data("whole")) * 100);
		var current_usage = (chart.data("part") / chart.data("whole")) * 100;
		var total_usage = Math.floor(((extraPart + chart.data("part")) / chart.data("whole")) * 100);

		// Determine what color the added usage should be
		var barColor = this.choose_color(total_usage);
		
		var fill_more = $('<div/>', {
			'class': barColor,
		});


		var under_quota;
		// Make sure they won't exceed 100% with added usage
		if (total_usage > 100) {

			if (this.quota_type == 'disk') {
				chart_info.html('<strong>Quota exceeded.</strong> Choose a smaller size, delete an existing volume, or request more resources.');	
			}
			else if (this.quota_type == 'disk_count') {
				chart_info.html('<strong>Quota exceeded.</strong> Delete an existing volume or request more resources.');
			}
			else {
				chart_info.html('<strong>Quota exceeded.</strong> Choose a smaller size or terminate a running instance.');
			}

			cssPercent = Math.floor(((chart.data("whole") - chart.data("part")) / chart.data("whole")) * 100);
			under_quota = false;
		}
		else {
			under_quota = true;

			var newPart = (chart.data("part") + extraPart);
			var newWhole = chart.data("whole");

			if (this.quota_type == 'mem') {
				var digits = (newPart % 1024 == 0) ? 0 : 1;
				newPart = (newPart > 1024) ? ('' + (newPart/1024).toFixed(digits)) : ('' + newPart + ' MB');
				newWhole /= 1024;
			}
			chart_info.html('You would use ' + newPart  + ' of your ' + newWhole + " allotted " + chart.data("unit"));
		}
	
		fill_more.attr("style", "width: " + cssPercent + "%");

        var total_percent = Math.round(((extraPart + chart.data("part")) / chart.data("whole")) * 100);

		if (fill.length != 0 && current_usage < 100) {
			fill.html('<span>' + total_percent + '%</span>');
			fill.attr("class", barColor);
			fill.addClass("barFlushLeft");

			chart.html(fill);
			fill_more.addClass("addedUsageBar");
		}
		else {
			fill_more.html('<span>' + total_usage + '%</span>');

			// If user has no existing quota and we're showing projected usage, show lower opacity
			if (self.is_initial) {
				fill_more.css('opacity', 0.5);
				fill_more.css('color', '#000');
			}
		}

        

	
		if (current_usage < 100) {
			chart.append(fill_more);
			return under_quota;
		}
		else {
			
			fill.html('<span>' + total_usage + '%</span>');
			chart.html(fill);

			if (Atmo.profile.get('quota_cpu') == -1 && Atmo.profile.get('quota_mem') == -1) {
				return true;
			}
			else {
				return under_quota;
			}
		}

	}
});

