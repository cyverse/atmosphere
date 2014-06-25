Atmo.Views.SettingsScreen = Backbone.View.extend({
    className: 'screen',
    template: _.template(Atmo.Templates['settings_screen']),
	initialize: function() {

        // Will need to bind: if user changed info about an identity, this.rerender_provider_data.

	    Atmo.profile.bind("change", this.render, this);
        this.rendered = false;
	},
    events: {
        'change form[name="settings"]' : 'update_settings',
        'click #icon_set_icons a' : 'update_icons',
	'submit form[name="add_new_identity"]':'add_new_identity',
	'change input[name="selected_identity"]' : 'switch_identity',
	'click .image-overview' : 'expand_details'
    },
    render: function() {
        if (Atmo.profile.isNew() || this.rendered)
            return this;

        this.$el.html(this.template(Atmo.profile.attributes));

        // Select all of the form elements based on their profile settings
        var settings = Atmo.profile.attributes.settings;
        
        this.$el.find('select[name="default_vnc"]').val(settings.default_vnc);
        this.$el.find('input[name="quick_launch"]').prop('checked', settings.quick_launch);
        this.$el.find('input[name="send_emails"]').prop('checked', settings.send_emails);

        // Show the selected background image and image/instance icon set
        this.$el.find('a[data-iconset="'+settings.icon_set+'"]').addClass('selected');

        // Properly change the caret when navigating in between Identity accordion tabs
        this.$el.find('.accordion-body').on('hidden', function() {
            $(this).siblings('.accordion-heading').removeClass('dropup');
        });
        this.$el.find('.accordion-body').on('shown', function() {
            $(this).siblings('.accordion-heading').addClass('dropup');
        });

		// Show user's available identities
		var self = this;
	
		for (var i = 0; i < Atmo.identities.length; i++) {
			var identity = Atmo.identities.models[i];

			// Create a summary for each view and identity
			var identity_view = new Atmo.Views.SettingsScreenIdentitySummary({
				provider: identity.get('provider_id'), 
				identity_id: identity.get('id')
			});
			self.$el.find('#providers').prepend(identity_view.render().el);
		}

		// Do initial population of histories
		this.populate_histories();

        this.rendered = true;

		return this;
	},
	populate_histories: function() {
		// Render pagination buttons

		var self = this;
		var provider = Atmo.profile.get('selected_identity').get('provider_id');
		var identity = Atmo.profile.get('selected_identity').get('id');

		// Grab first page of machine history
		$.ajax({
			type: 'GET',
			url: site_root + '/api/v1/provider/' + provider + '/identity/' + identity + '/machine/history/?page=1', 
			success: function(response_text) {

				// Loop through given instances and append them.
				var container = self.$el.find('#profile_image_list');
				var machines = response_text.results;

				if (machines.length == 0)
					container.find('td').html('You have not imaged any of your instances yet.');
				else
					container.empty();

				for (var i = 0; i < machines.length; i++) {
					container.append(_.template(Atmo.Templates['machine_history_row'], machines[i]));
				}
			},
			error: function() {
			}
		});
		// Grab first page of instance history
		$.ajax({
			type: 'GET',
			url: site_root + '/api/v1/provider/' + provider + '/identity/' + identity + '/instance/history/?page=1', 
			success: function(response_text) {

				// Loop through given instances and append them.
				var container = self.$el.find('#profile_instance_list');
				var instances = response_text.results;

				if (instances.length == 0)
					container.find('td').html('You have not launched any instances yet');
				else
					container.empty();

				for (var i = 0; i < instances.length; i++) {
                    instance = instances[i]
                    if (instance.start_date.length == 24) {
                        instance.start_date = instance.start_date.split('.')[0] + 'Z'
                    }
                    instance.start_date_p = Date.parse(instance.start_date)
                    if (instance.start_date_p != null)
                        instance.start_date =instance.start_date_p.format("MM/dd/yyyy II:mm p")
                    if (instance.end_date != null) {
                        if (instance.end_date.length == 24) {
                            instance.end_date = instance.end_date.split('.')[0] + 'Z'
                        }
                        instance.end_date_p = Date.parse(instance.end_date)
                    }
                    if (instance.end_date_p != null)
                        instance.end_date = instance.end_date_p.format("MM/dd/yyyy II:mm p")
                    instance.active_time = Atmo.Utils.seconds_to_pretty_time(parseFloat(instance.active_time), 1)
					container.append(_.template(Atmo.Templates['instance_history_row'], instance));
				}
			},
			error: function() {
			}
		});

	},
	switch_identity: function() {
		var self = this;
		var id = parseInt(self.$el.find('input[name="selected_identity"]:checked').val());
		Atmo.profile.save(
			{ 'selected_identity' : id },
			{ async : false, 
			patch: true, 
			success: location.reload() }
		);	
		location.reload();
	},
	add_new_identity: function(e) {
		e.preventDefault();

		var data = {};
        data['message'] = 'Atmosphere User ' + Atmo.profile.get('id') + ' wants to add ' + this.$el.find('select[name="cloud_provider"]').val();
		data['username'] = Atmo.profile.get('id');
        data['subject'] = 'Atmosphere User ' + Atmo.profile.get('id') + ' wants to add ' + this.$el.find('select[name="cloud_provider"]').val();

        this.$el.find('#request_new_identity').val('Sending...').attr('disabled', 'disabled');

        var self = this;

        $.ajax({
            type: 'POST',
            url: site_root + '/api/v1/email/support/', 
            data: data,
            statusCode: {
                200: function() {
                    self.$el.find('#request_new_identity').val('Request New Identity').removeAttr('disabled', 'disabled');
					Atmo.Utils.notify('Request Submitted', 'Support will contact you shortly about adding a new cloud identity.');
                }
            },
        });
        return false;
	},
    /*edit_login_key: function(e) {
            e.preventDefault();

            var header = 'Edit Cloud Identity';
            var content = '<form name="update_identity">';
            content += '<label for="login">Username</label>';
            content += '<input type="text" name="login" disabled="disabled" placeholder="'+Atmo.profile.get('id')+'"><br />';
            content += '<label for="key">Password</label>';
            content += '<span class="help-block"><a href="https://user.iplantcollaborative.org/reset/request">Reset Your Password</a></span>';
            content += '<label for="alias">New Alias</label>';
            content += '<input type="text" name="alias" value="' + Atmo.profile.get('id') + '" />';
            content += '</form>';

            Atmo.Utils.confirm(header, content, { on_confirm: function() {
                // Update stuff
            }, 
                ok_button: 'Update Identity'
            });

    },*/
    update_icons: function(e) {
        this.$el.find('#icon_set_icons li a').removeClass('selected');
        $(e.target).parent().addClass('selected');

        var loader = $('<span/>', {
            class: 'inline-help',
            style: 'margin-left: 10px;',
            html: '<img src="'+site_root+'/resources/images/loader.gif"> Updating'
        });
        this.$el.find('label[for="icon_set"]').find('span').remove();
        this.$el.find('label[for="icon_set"]').append(loader);

		// Need this incase user clicks on image instead of link
        var val = $(e.target).data('iconset') || $(e.target).parent().data('iconset');
        var self = this;   

		if (typeof(val) != 'undefined') {
			Atmo.profile.save(
				{ icon_set: val },
				{ patch: true,
				async: false,
				success: function() {
                    loader.html('<i class="icon-ok"></i> Updated. Application will refresh with changes.');
                    setTimeout(function() {
                        loader.fadeOut('fast', function() {
                            $(this).remove(); 
							location.reload();
                        });
                    }, 5 * 1000);
				}, 
				error: function() {
                    // Inform user that the setting was NOT successfully updated.
                    loader.html('<i class="icon-warning-sign"></i> Update Failed. Please contact support.');                    
                    setTimeout(function() {
                        loader.fadeOut('fast', function() {
                            $(this).remove(); 
                            self.rendered = false;
                            self.render();
                        });
                    }, 5 * 1000);
				}
			});
		}
		else {
			loader.html('<i class="icon-warning-sign"></i> Invalid icon selection.');                    
		}
    }, 
    update_settings: function(e) {
        var val, input;
        var setting = e.target.name;
        if (this.$el.find('input[name="'+setting+'"]').length != 0) {

            var input = this.$el.find('input[name="'+setting+'"]');

            // Different behavior for different kinds of inputs
            if (this.$el.find('input[name="'+setting+'"][type="checkbox"]').length != 0) {
               val = (input.prop('checked') == true) ? true : false;
            }

            //val = this.$el.find('input[name="'+setting+'"]').val();
        }
        else if (this.$el.find('select[name="'+setting+'"]').length != 0) {
            input = this.$el.find('select[name="'+setting+'"]');
            val = this.$el.find('select[name="'+setting+'"]').val();
        }
        else {
            // Will need more options if more form types are introduced
        }

        // Update the backbone models
        Atmo.profile.attributes.settings[setting] = val;

        var data = {};
        data[setting] = val;

        // Spinning spinner
        var loader = $('<span/>', {
            class: 'inline-help',
            style: 'margin-left: 10px;',
            html: '<img src="'+site_root+'/resources/images/loader.gif"> Updating'
        });

        input.parent().find('span').remove();
        input.parent().append(loader);


        var self = this;
        
        if (val != undefined) {
			Atmo.profile.save(data, {
				patch: true,
				success: function() {
                    loader.html('<i class="icon-ok"></i> Updated');                    
                    setTimeout(function() {
                        loader.fadeOut('fast', function() {
                            $(this).remove(); 
                        });
                    }, 5 * 1000);
				},
				error: function() {
                    loader.html('<i class="icon-warning-sign"></i> Update Failed. Please contact support.');                    
                    setTimeout(function() {
                        loader.fadeOut('fast', function() {
                            $(this).remove(); 
                            self.rendered = false;
                            self.render();
                        });
                    }, 5 * 1000);
				}
			});
        }
    },
	expand_details: function(e) {
		var details = $(e.currentTarget).next();
		if (details.is(':visible'))
			details.hide();
		else
			details.show();
	}
});
