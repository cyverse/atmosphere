/**
 *
 * Restores a volume the user had backed-up to IRODS by overwriting an existing volume.
 *
 */
define(['backbone', 'templates'], function(Backbone, Templates) {

var RestoreVolumeModal = Backbone.View.extend({
    id: 'restore_modal',
    className: 'modal fade',
    template: _.template(Templates.restore_volume_modal),
    initialize: function(options) {
        this.instances = options.instances;
        this.volumes = options.volumes;
		this.volumes.bind("reset", this.render, this);
		this.volumes.bind("add", this.render, this);
		this.volumes.bind("remove", this.render, this);
    },
    render: function() {
        this.$el.html(this.template());

		// Populate modal with volumes
		if (this.volumes.length > 0) {
			this.$el.find('select[name="destination_volume"]').children().eq(0).remove();

			for (var i = 0; i < this.volumes.models.length; i++) {
				this.$el.find('select[name="destination_volume"]').append($('<option>', {
                    html: function() {
						var content = '';
						content += this.volumes.models[i].get('name_or_id');

						// If the volume has a name, show ID in parens
						if (this.volumes.models[i].get('name') != this.volumes.models[i].get('id'))
							content += ' (' + this.volumes.models[i].get('id') + ')';

						return content;
					},
					value: this.volumes.models[i].get('id')
				}));
			}
		}

        return this;
    },
    do_alert: function() {

        this.$el.modal({
            backdrop: true,
            keyboard: true
        });

        this.$el.find('.modal-header button').click(function() {
            this.$el.modal('hide');
        });

        this.$el.modal('show');

        this.$el.find('.modal-footer a').unbind('click');

		// Allow user to confirm with enter key
        $(window).on('keyup', function(e) {

            // Only confirm if user does not have cursor in a textarea
            if (e.keyCode == 13 && $('textarea:focus').length == 0) {
                this.$el.find('.modal-footer a').eq(1).trigger('click');
            }
        });
        
        this.$el.find('.modal-footer a').show();
        this.$el.find('.modal-footer a').eq(0).click(this.button_listener);
        this.$el.find('.modal-footer a').eq(1).click(this.start_volume_restore);
    },
	button_listener: function(callback) {
		var self = this;
		return function(e) {
			e.preventDefault();
			self.$el.modal('hide');
			$('.modal-backdrop').remove();
			if (callback != undefined) 
				callback();
			$(window).unbind('keyup');
		}
	},
	start_volume_restore: function() {

		// Do all the confirmation stuff here, then actually perform restore

		this.$el.find('.modal-footer a').eq(1).click(this.button_listener(this.confirm_restore));
	},
	confirm_restore: function(e) {
	
		// Begin restore process

	}
});


return RestoreVolumeModal;

});
