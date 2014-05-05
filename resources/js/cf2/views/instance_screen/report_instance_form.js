/**
 *
 * Reports a broken instance to Atmosphere's support team.
 *
 */
Atmo.Views.ReportInstanceForm = Backbone.View.extend({
	'tagName': 'div',
    'className': 'report_instance_form',
	template: _.template(Atmo.Templates.report_instance_form),
    events: {
        'click .report_instance_submit' : 'send_request',
        'keyup textarea[name="problem_description"]' : 'validate_form'
    },
	initialize: function() {
	},
	render: function() {
		this.$el.html(this.template(this.model.toJSON()));
		return this;
	},
    validate_form: function(e) {
        if (e != undefined) e.preventDefault();

        var valid = true;

        this.$el.find('.help-block').remove();
        this.$el.find('div').removeClass('error');

        if (this.$el.find('textarea[name="problem_description"]').val().length == 0) {
            valid = false;
            this.$el.find('label[for="problem_description"]').after($('<span/>', {
                class: 'help-block',
                html: 'Please provide a description of the problem.'
            }));
            this.$el.find('textarea[name="problem_description"]').closest('.control-group').addClass('error');
        }
        if (this.$el.find('input[type="checkbox"]:checked').length == 0) {
            this.$el.find('label[for="problem_type"]').after($('<span/>', {
                class: 'help-block',
                html: 'Please select at least one problem.'
            }));
            this.$el.find('label[for="problem_type"]').closest('.control-group').addClass('error');
            valid = false;
        }
        
        return valid;

    },
    send_request: function(e) {
        e.preventDefault();

        if (this.validate_form(e)) {

            var self = this;

            var data = {};
            data["username"] = Atmo.profile.get('id');
            data["message"] = 'Instance IP: ' + this.model.get('public_dns_name') + '\n';
            data["message"] += 'Instance ID: ' + this.model.get('id') + '\n\n';
            data["message"] += 'Problems:\n';

            var checkboxes = this.$el.find('input[type="checkbox"]:checked');
            for (var i = 0; i < checkboxes.length; i++) {
                data["message"] += '\t- ' + $(checkboxes[i]).val() + '\n';
            }
            data["message"] += 'Description: ' + this.$el.find('textarea[name="problem_description"]').val();
            data["subject"] = 'Atmosphere Instance Report from ' + data["username"];

			// Create a list of user's instances and volumes to make support easier
			data["message"] += '\n---\n\n';
			data["message"] += 'Provider ID: ' + Atmo.profile.get('selected_identity').get('provider_id') + '\n\n';
			data["message"] += '\n---\n';
			data["message"] += '\n\n' + Atmo.profile.get('id') + "'s Instances:";
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

            var btn = self.$el.find('.report_instance_submit');

            btn.val("Submitting Report...")
                .removeClass("btn-primary")
                .click(function() { return false; });
            var loader = $('<img/>', {
                src: site_root + '/resources/images/loader.gif',
                style: 'margin-right: 10px;'
            });
            btn.before(loader);

            $.ajax({
                type: 'POST',
                url: site_root + '/api/v1/email/support/', 
                data: data,
                success: function() {
					loader.remove();
					btn.val("Report Submitted")
						.attr("disabled", "disabled")
					btn.after($('<a/>', {
						href: '#',
						style: 'margin-left: 10px;',
						html: 'Send another report',
						click: function(e) {
							e.preventDefault();
							self.render();
						}
					}))
					.after("Your report has been sent to support. Reports are typically answered in one to two business days.");
				},
				error: function() {
					loader.remove();
					btn.val("Report Submitted")
						.attr("disabled", "disabled")
					Atmo.Utils.notify('Could not send report', 'Please email your issue directly to <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>.');
				},
            });
        }
        return false;

    }
});
