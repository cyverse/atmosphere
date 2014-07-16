/**
 *
 * Validates and sends an imaging request for the selected instance.
 *
 */
Atmo.Views.RequestImagingForm = Backbone.View.extend({
	'tagName': 'div',
	'className' : 'imaging_form module',
	template: _.template(Atmo.Templates.request_imaging_form),
    events: {
        'submit .request_imaging_form' : 'send_request',
		'click #licensed_software' : 'certify_image'
    },
	initialize: function() {
        this.tagger = null;
	},
	render: function() {
		this.$el.html(this.template(this.model.toJSON()));
        var self = this;
        this.tagger = new Atmo.Views.Tagger({
            change: function(tags) {
                self.$el.find('.tag_input').val(tags.join(','));
            }
        });
        this.tagger.render().$el.prependTo(this.$el.find('.tagger_container'));

		// Populate cloud for deployment only with user's available providers

		// Populate the top menu with a provider switcher 
		for (var i = 0; i < Atmo.identities.length; i++) {

			var identity = Atmo.identities.models[i];
			var name = Atmo.identities.models[i].get('provider').get('location');
            // Skip eucalyptus
            if (name.match(/eucalyptus/i))
                continue
			if (identity.get('selected'))
				this.$el.find('select[name="provider"]').prepend('<option value="' + identity.get('provider_id') + '">' + name + '</option>');
			else
				this.$el.find('select[name="provider"]').append('<option value="' + identity.get('provider_id') + '">' + name + '</option>');
		}

		return this;
	},
	certify_image: function(e) {

		if (this.$el.find('#licensed_software:checked').length == 1) {
			this.$el.find('#licensed_software').closest('.control-group').removeClass('error');
			this.$el.find('#licensed_software').closest('.controls').removeClass('alert-error').removeClass('alert');
		}
		else {
			this.$el.find('#licensed_software').closest('.control-group').addClass('error');
			this.$el.find('#licensed_software').closest('.controls').addClass('alert-error').addClass('alert');
		}

	},
    send_request: function(e) {
        e.preventDefault();

		if (this.$el.find('#licensed_software:checked').length == 0) {
			// You shall not pass!
			this.$el.find('#licensed_software').closest('.control-group').addClass('error');
			this.$el.find('#licensed_software').closest('.controls').addClass('alert-error').addClass('alert');
			return false;
		}

        var self = this;

        $.ajax({
            type: 'POST',
            url: site_root + '/api/v1/provider/'+Atmo.profile.get('selected_identity').get('provider_id') + '/identity/' + Atmo.profile.get('selected_identity').id + '/request_image/', 
            data: this.$el.find('.request_imaging_form').serialize(),
            success: function() {
                self.$el.find('.request_image_submit').val("Request Submitted!").attr("disabled", "disabled").click(function() { return false; });
            },
			error: function() {
				Atmo.Utils.notify("Could not submit request", 'If the problem persists, please email your request to <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
			},
            dataType: 'json'
        });

        return false;

    }
});
