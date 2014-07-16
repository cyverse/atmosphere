/**
 *
 * Reports a broken volume to Atmosphere's support team. 
 *
 */
Atmo.Views.ReportVolumeModal = Backbone.View.extend({
    id: 'report_modal',
    className: 'modal fade',
    template: _.template(Atmo.Templates.report_volume_modal),
	events: {
		'click #report_volume_confirm' : 'report_volume'
	},
    initialize: function() {
		Atmo.volumes.bind("reset", this.render, this);
		Atmo.volumes.bind("add", this.render, this);
		Atmo.volumes.bind("remove", this.render, this);
    },
    render: function() {

        this.$el.html(this.template());

		// Populate modal with volumes
		if (Atmo.volumes.length > 0) {
			this.$el.html(this.template());
			this.$el.find('select[name="broken_volume"]').children().eq(0).remove();

			for (var i = 0; i < Atmo.volumes.models.length; i++) {
				this.$el.find('select[name="broken_volume"]').append($('<option>', {
                    html: function() {
						var content = '';
						content += Atmo.volumes.models[i].get('name_or_id');

						// If the volume has a name, show ID in parens
						if (Atmo.volumes.models[i].get('name') != Atmo.volumes.models[i].get('id'))
							content += ' (' + Atmo.volumes.models[i].get('id') + ')';

						return content;
					},
					value: Atmo.volumes.models[i].get('id')
				}));
			}
		}
		else {
            var body = '<p class="alert alert-info"><i class="glyphicon glyphicon-info-sign"></i> You don\'t have any volumes.</p>'
            body += 'If you need help with something else, please contact the Atmosphere support team. You can: ';
            body += '<ul><li>Email <a href="mailto:atmo@iplantcollaborative.org">atmo@iplantcollaborative.org</a></li>';
            body += '<li>Use the feedback form by clicking the "Feedback &amp; Support" button in the footer</li></ul>';
            ok_button = 'Ok';

			this.$el.find('.modal-body').html(body);
		}

        return this;
    },
    do_alert: function() {
		var self = this;

        this.$el.modal({
            backdrop: true,
            keyboard: true
        });

        this.$el.find('.modal-header button').click(function() {
            this.$el.modal('hide');
        });

        this.$el.modal('show');

        $(window).on('keyup', function(e) {

            // Only confirm if user does not have cursor in a textarea
            if (e.keyCode == 13 && $('textarea:focus').length == 0) {
                this.$el.find('.modal-footer a').eq(1).trigger('click');
            }
        });
        
        this.$el.find('.modal-footer a').show();
        this.$el.find('.modal-footer a').eq(0).click(function() { self.button_listener() });
    },
	button_listener: function(callback) {
		var self = this;

		self.$el.modal('hide');
		$('.modal-backdrop').remove();
		if (callback != undefined) 
			callback();
		$(window).unbind('keyup');
	},
	report_volume: function(e) {
		var data = {};
		var self = this;

		var inputs = $('form[name="report_volume_form"] select, form[name="report_volume_form"] textarea');
		var selects = $('form[name="report_volume_form"] input[type="checkbox"]');

		var num_inputs = 0;

		// Only fetch values from selected checkboxes

		for (var i = 0; i < selects.length; i++) {
			if ($(selects[i]).is(':checked')) {
				inputs.push(selects[i]);
				num_inputs++;
			}
		}

		// Error handling: Require user to fill out both checkboxes and the textarea

		if (num_inputs == 0 || $('form[name="report_volume_form"] textarea').val().length == 0) {
			this.$el.find('.alert').removeClass('alert-info').addClass('alert-error').html(function() {
				var content = '<i class="glyphicon glyphicon-warning-sign"></i> ';
				content += 'Volume report cannot be blank. Please include more information about the problem.';
				return content;
			});

			if (num_inputs == 0)
				this.$el.find('input[type="checkbox"]').closest('.control-group').addClass('error');
			else
				this.$el.find('input[type="checkbox"]').closest('.control-group').removeClass('error');

			if (this.$el.find('textarea').val().length == 0)
				this.$el.find('textarea').closest('.control-group').addClass('error');
			else
				this.$el.find('textarea').closest('.control-group').removeClass('error');

			return false;

		}
		else {	
			// Add all inputs to outgoing message
			data["message"] = '';
			data["username"] = Atmo.profile.get('id');
			data["subject"] = 'Atmosphere Volume Report from ' + data["username"];
			for (var i = 0; i < inputs.length; i++) {

				data["message"] += $(inputs[i]).val() + '\n';

				if ($(inputs[i]).attr('type') != 'checkbox') {
				   data["message"] += '\n';
				}

			}

			data["message"] += '\n---\n\n';
			data["message"] += 'Provider ID: ' + Atmo.profile.get('selected_identity').get('provider_id') + '\n\n';

			// Create a list of user's instances and volumes to make support easier
			data["message"] += '\n\n' + Atmo.profile.get('id') + "'s Instances:";
			data["message"] += '\n---\n';
			for (var i = 0; i < Atmo.instances.length; i++) {
				var instance = Atmo.instances.models[i];
				data["message"] += '\nInstance id:\n\t' + instance.get('id') + '\nEMI Number:\n\t' + instance.get('image_id') + '\nIP Address:\n\t' + instance.get('public_dns_name') + '\n';
			}
			data["message"] += '\n\n' + Atmo.profile.get('id') + "'s Volumes:";
			data["message"] += '\n---\n';
			for (var i = 0; i < Atmo.volumes.length; i++) {
				var volume = Atmo.volumes.models[i];
				data["message"] += '\nVolume id:\n\t' + volume.get('id') + '\nVolume Name:\n\t' + volume.get('name');
			}
			data["message"] += '\n\n';

			data['location'] = window.location.href,
			data['resolution'] = { 
				'viewport': {
					'width': $(window).width(),
					'height': $(window).height()
				},
				'screen': {
					'width':  screen.width,
					'height': screen.height
				}
			};

			var succeeded = true;

			$.ajax({
				type: 'POST',
				url: site_root + '/api/v1/email/support/', 
				data: data,
				success: function() {
					// Clean out the form for next time
					self.render();

					// Close the window
					self.button_listener(Atmo.Utils.notify("Volume Reported", "Support will contact you shortly"));
				},
				error: function() {
					self.$el.find('.alert').removeClass('alert-info').addClass('alert-error').html(function() {
						var content = '<i class="glyphicon glyphicon-warning-sign"> ';
						content += 'Unable to report volume. Please email your report to <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>.';
					});

					// Allow user to copy their message into an email since API failed
					succeeded = false;
					
				},
				dataType: 'json'
			});

			return succeeded;
		}
	}
});
