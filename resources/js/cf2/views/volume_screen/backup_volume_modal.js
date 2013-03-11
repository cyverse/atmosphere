Atmo.Views.BackupVolumeModal = Backbone.View.extend({
    id: 'backup_modal',
    className: 'modal hide fade',
    template: _.template(Atmo.Templates.backup_volume_modal),
	events: {
		'change select[name="volume_to_backup"]' : 'backup_location_change',
		'submit form[name="backup_volume_form"]' : 'backup_volume',
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
        $('#backup_modal').modal({
            backdrop: true,
            keyboard: true
        });

        $('#backup_modal .modal-header button').click(function() {
            $('#backup_modal').modal('hide');
        });

        $('#backup_modal').modal('show');

        $('#backup_modal .modal-footer a').unbind('click');

        var button_listener = function(callback) {
            return function(e) {
                e.preventDefault();
                $('#backup_modal').modal('hide');
                $('.modal-backdrop').remove();
                if (callback != undefined) 
                    callback();
                $(window).unbind('keyup');
            }
        }

        $(window).on('keyup', function(e) {

            // Only confirm if user does not have cursor in a textarea
            if (e.keyCode == 13 && $('textarea:focus').length == 0) {
                $('#backup_modal .modal-footer a').eq(1).trigger('click');
            }
        });
        
        $('#backup_modal .modal-footer a').show();
        $('#backup_modal .modal-footer a').eq(0).click(button_listener());
    },
	backup_location_change: function(e) {
		selected_vol = this.$el.find('select[name="volume_to_backup"] option:selected').val();

		this.$el.find('input[name="backup_location"]').val('/home/iplant/' + Atmo.profile.get('id') + '/atmo/' + selected_vol);
	},
	backup_volume: function(e) {
		e.preventDefault();
		console.log("backup");
	},
});
