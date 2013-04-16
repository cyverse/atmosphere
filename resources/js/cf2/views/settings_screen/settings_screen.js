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
        'click #help_edit_login_key' : 'edit_login_key',
		'submit form[name="add_new_identity"]':'add_new_identity',
		'change input[name="selected_identity"]' : 'switch_identity'
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
		this.identities = {};
	
		// This should be replaced and put in a model
        $.ajax({
            type: 'GET',
            url: site_root + '/api/group/', 
            success: function(response_text) {
				self.identities = response_text[0].identities;

                // Create a summary for each view and identity
                for (var i = 0; i < self.identities.length; i++) {
                    var identity = new Atmo.Views.SettingsScreenIdentitySummary({
                        provider: self.identities[i].provider_id, 
                        identity_id: self.identities[i].id
                    });
                    self.$el.find('#providers').prepend(identity.render().el);
                }
            },
			error: function() {
				Atmo.Utils.notify("Could not load all cloud identities", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
			},
            dataType: 'json'
        });

		/*

		Disabled until we have settings for each provider

		if (Atmo.instance_types.models.length > 0) {
			$.each(Atmo.instance_types.models, function(idx, instance_type) {
				var opt = $('<option>', {
					value: instance_type.get('name'),
					html: function() {
						return instance_type.get('name') + ' (' + instance_type.get('cpus') + ' CPUs, ' + instance_type.get('mem') + ' GB memory, ' + instance_type.get('disk') + ' GB disk)';
					},
				});
				self.$el.find('select[name="default_size"]').append(opt);
			});

			this.$el.find('select[name="default_size"]').val(settings.default_size);
		}
		else {
			this.$el.find('select[name="default_size"]').html($('<option>', {
				html: 'Instance Sizes Unavailable',
				disabled: 'disabled'
			})).after('<div class="alert alert-error"><button type="button" class="close" data-dismiss="alert">&times;</button><strong>Could not get instance types</strong> Please contact support if the problem persists.</div>');
		}*/

        this.rendered = true;

		return this;
	},
	switch_identity: function() {
		var self = this;
		var id = parseInt(self.$el.find('input[name="selected_identity"]:checked').val());
		Atmo.profile.save(
			{ 'selected_identity' : id },
			{ async : false }
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
            url: site_root + '/api/email_support/', 
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
    edit_login_key: function(e) {
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

    },
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

        var val = $(e.target).parent().data('iconset');
        var data = {};
        data["icon_set"] = val;

        var self = this;   

        if (val != undefined) {
            $.ajax({
                type: 'PUT',
                url: site_root + '/api/profile/', 
                data: data,
                success: function() {
                    loader.html('<i class="icon-ok"></i> Updated. Refresh to see new icons.');
                    Atmo.instances.update();
                    Atmo.images.fetch();
                    setTimeout(function() {
                        loader.fadeOut('fast', function() {
                            $(this).remove(); 
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
                },  
                dataType: 'JSON'
            }); 
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
            $.ajax({
                type: 'PUT',
                url: site_root + '/api/profile/', 
                data: data,
                success: function() {
                    // Inform user that the setting was successfully updated.
                    loader.html('<i class="icon-ok"></i> Updated');                    
                    setTimeout(function() {
                        loader.fadeOut('fast', function() {
                            $(this).remove(); 
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
                },  
                dataType: 'JSON'
            }); 
        }
        

    }
});
