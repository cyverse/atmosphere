/**
 *
 * Backs up a volume in user's IRODS directory. 
 *
 */
Atmo.Views.BackupVolumeModal = Backbone.View.extend({
    id: 'backup_modal',
    className: 'modal fade',
    template: _.template(Atmo.Templates.backup_volume_modal),
	events: {
		'change select[name="volume_to_backup"]' : 'backup_location_change',
		'input input[name="backup_name"]' : 'validate_backup_name'
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
			this.$el.find('select[name="volume_to_backup"]').children().eq(0).remove();

			for (var i = 0; i < Atmo.volumes.models.length; i++) {
				this.$el.find('select[name="volume_to_backup"]').append($('<option>', {
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
			
			this.$el.find('select[name="volume_to_backup"]').trigger('change');

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
        this.$el.find('.modal-footer a').eq(1).click(this.begin_backup);
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
	validate_backup_name: function() {

		var volume_name = this.$el.find('input[name="backup_name"]').val();
		var volume_name_field = this.$el.find('input[name="backup_name"]');

		this.$el.find('#backup_name_errors').html("<ul></ul>");
		var errors = false;

		// Make sure volume name doesn't contain spaces
		if (volume_name.indexOf(' ') != -1) {
			// Tell them there's a problem
			this.$el.find('#backup_name_errors ul').append("<li>Volume names may not contain spaces.</li>");
			volume_name_field.closest('.control-group').addClass('error');
			this.$el.find('#confirm_backup').attr('disabled', 'disabled');
			errors = true;
		}
		var exp = /^[a-zA-Z0-9_]*$/gi;
		if (exp.test(volume_name) == false) {
			this.$el.find('#backup_name_errors ul').append("<li>Volume name may contain only numbers, letters, and underscores.</li>");
			this.$el.find('#confirm_backup').attr('disabled', 'disabled');
			volume_name_field.closest('.control-group').addClass('error');
			errors = true;
		}

		if (!errors) {
			// No errors yet means that volume_name is ok
			volume_name_field.closest('.control-group').removeClass('error');

			// Update the backup location with backup name if applicable 
			if (volume_name.length > 0)
				this.$el.find('input[name="backup_location"]').val('/home/iplant/' + Atmo.profile.get('id') + '/atmo/' + volume_name);
			else {
				selected_vol = this.$el.find('select[name="volume_to_backup"] option:selected').val();
				this.$el.find('input[name="backup_location"]').val('/home/iplant/' + Atmo.profile.get('id') + '/atmo/' + selected_vol);
			}

			this.$el.find('#confirm_backup').removeAttr('disabled', 'disabled');
		}

		return errors;

	},
	backup_location_change: function(e) {
		selected_vol = this.$el.find('select[name="volume_to_backup"] option:selected').val();

		if (this.$el.find('input[name="backup_name"]').val().length == 0)
			this.$el.find('input[name="backup_location"]').val('/home/iplant/' + Atmo.profile.get('id') + '/atmo/' + selected_vol);
	},
	begin_backup: function() {

		if (this.validate_backup_name()) {
			this.$el.find('.modal-footer a').eq(1).unbind('click');
			this.$el.find('.modal-footer a').eq(1).click(this.button_listener(this.complete_backup));


		}
		
		return false;
	},
	complete_backup: function(e) {
		

	}
});
