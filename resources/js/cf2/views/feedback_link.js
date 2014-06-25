/**
 *
 * View for user-submitted feedback. 
 *
 */
Atmo.Views.FeedbackLink = Backbone.View.extend({
	initialize: function() {
		var self = this;
		this.$el.popover({
			placement : 'top',
			title: 'Feedback Form <a class="close" data-dismiss="popover" href="#">&times</a>',
            html: true,
			trigger: 'click',
            content: _.template(Atmo.Templates.feedback_form),
		}).click(function() {
			$('a[data-dismiss="popover"]').click(_.bind(self.cancel_popover, self));
			$('#cancel_popover').click(_.bind(self.cancel_popover, self));
			$('#submit_feedback').click(_.bind(self.submit_feedback, self));
		});
	},
	cancel_popover: function(e) {
		e.preventDefault();
		this.$el.popover('hide');
	},
	submit_feedback: function(e) {
		e.preventDefault();

		var data = {
			'location': window.location.href,
			'resolution': { 
				'viewport': {
					'width': $(window).width(),
					'height': $(window).height()
				},
		   		'screen': {
					'width':  screen.width,
					'height': screen.height
				}
			}
		};

		data["message"] = $('#feedback').val();

		// Create a list of user's instances and volumes to make support easier
		data["message"] += '\n---\n\n';
		data["message"] += 'Provider ID: ' + Atmo.profile.get('selected_identity').get('provider_id') + '\n\n';
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

		var self = this;

		if ($('#feedback').val().length > 0) {

			$('#submit_feedback').html('<img src="'+site_root+'/resources/images/loader.gif" /> Sending...').attr('disabled', 'disabled');				

			$.ajax(site_root + '/api/v1/email/feedback/', {
				type: 'POST',
				data: data,
				success: function(data) {

					// setTimeout to prevent loader gif from flashing on fast responses
					setTimeout(function() {

						$('#feedback_link').popover('hide');

						Atmo.Utils.notify("Thanks for your feedback!", "Support has been notified.");

						self.$el.popover({
							placement : 'top',
							title: 'Thanks for your feedback! <a class="close" data-dismiss="popover" href="#">&times</a>',
							html: true,
							trigger: 'click',
							content: function() {
								var form = $('<form>');
								form.append($('<span>', {
									'class': 'help-block',
									html: 'Feel free to submit additional comments.'
								}));
								var textarea = $('<textarea/>', {
									rows: '5',
									id: 'feedback'
								});
								form.append(textarea);
								form.append($('<button>', {
									'class': 'btn btn-primary',
									html: 'Send',
									id: 'submit_feedback',
									type: 'submit',
								}));
								form.append($('<a/>', {
									'class': 'btn',
									href: '#',
									html: 'Cancel',
									id: 'cancel_popover',
								}));
								return form;
							}
						}).click(function() {
							$('a[data-dismiss="popover"]').click(_.bind(self.cancel_popover, self));
							$('#cancel_popover').click(_.bind(self.cancel_popover, self));
							$('#submit_feedback').click(_.bind(self.submit_feedback, self));
						});
													
						setTimeout(function() {
							$('#feedback_link').popover('hide');
						}, 5*1000);
					}, 2*1000);
				}, 
				error: function(response_text) {
					Atmo.Utils.notify("An error occured", 'Your feedback could not be submitted. If you\'d like to send it directly to support, email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>.');
				}
			});
		}
	}
});
