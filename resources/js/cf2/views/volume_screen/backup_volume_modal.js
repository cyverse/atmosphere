Atmo.Views.BackupVolumeModal = Backbone.View.extend({
    id: 'backup_modal',
    className: 'modal hide fade',
    template: _.template(Atmo.Templates.backup_volume_modal),
	events: {
		'change select[name="volume_to_backup"]' : 'backup_location_change'
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
	backup_location_change: function(e) {
		selected_vol = this.$el.find('select[name="volume_to_backup"] option:selected').val();

		this.$el.find('input[name="backup_location"]').val('/home/iplant/' + Atmo.profile.get('id') + '/atmo/' + selected_vol);
	},
	begin_backup: function() {
		console.log("backup");
		
		this.$el.find('.modal-footer a').eq(1).unbind('click');
        this.$el.find('.modal-footer a').eq(1).click(this.button_listener(this.complete_backup));
	},
	complete_backup: function(e) {
		
		console.log("complete backup");

	}
});
