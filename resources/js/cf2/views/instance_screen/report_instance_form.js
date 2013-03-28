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

            console.log(data);
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
                url: site_root + '/api/email_support/', 
                data: data,
                statusCode: {
                    200: function() {
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
                    }
                },
                contentType: 'json',
                dataType: 'json'
            });
        }
        return false;

    }
});
