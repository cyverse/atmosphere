/**
 * Represents a single volume on the volume screen, regardless of whether it is
 * available or attached
 */
Atmo.Views.VolumeScreenVolume = Backbone.View.extend({
    tagName: 'li',
    className: 'draggable_volume',
    events: {
        'click span': 'x_clicked',
    },
    initialize: function() {
        this.model.bind("remove", this.remove, this);
        this.model.bind('change:status', this.update_volume_info, this);
    },
    render: function() {
        this.$el
            .append($('<strong>').append( this.model.get('name_or_id') ))
            .append(' (' + this.model.get('size') + ' GB) ')
            .append(
                $('<span>').append($('<img>', { src: '../resources/images/x_close.png' } ))
            )
            .draggable({revert: 'invalid', disabled: true})
            .data('volume', this.model);
        this.update_volume_info();
        return this;
    },
    update_volume_info: function() {
        // Update the view based on its status
        this.$el
            // set the class name
            .removeClass('unattached attached attaching')
            .addClass(this.model.get('status') == 'available' ? 'unattached' : 'attached')
            // update the hover title on the X button
            .find('span')
                .attr('title', this.model.get('status') == 'available' ? 'Destroy Volume' : 'Detach Volume')
                .end()
            // remove the 'attaching' spinner
            .find('.volume_info')
                .remove()
                .end()
            // Disable draggable if attaching/detaching
            .draggable('option', 'disabled', this.model.get('status') == 'attaching' || this.model.get('status') == 'detaching');

        if (this.model.get('status') == "attaching") 
            this.$el
                .addClass('attaching')
                .append('<div class="volume_info">Device Location: <span data-id="'+this.model.get('id')+'"><img src="../resources/images/loader.gif" /> Attaching</span></div>');
        else if (this.model.get('status') == 'detaching') {
            //TODO: This is a hack to get 'detaching' volumes to revert to their original position.. Css/js wizards approval required
            this.$el.removeAttr('style')
            this.$el
                .addClass('attaching')
                .append('<div class="volume_info"><span data-id="'+this.model.get('id')+'"><img src="../resources/images/loader.gif" /> Detaching</span></div>');
        }
        else if (this.model.get('status') == 'in-use') {
            this.$el
                .addClass('attached')
                .append('<div class="volume_info">Device location: <span class="vol_loc" data-id="' + this.$el.get('id') + '">' + this.model.get('attach_data_device') + '</span></div>');

        }
    },
    x_clicked: function(e) {
        // when the x is clicked, either destroy the volume or detach it
        var self = this;
        if (this.model.get('status') == 'available') {

            // Destroy the volume
            self.model.confirm_destroy({
                success: function() {
                    window.app.navigate('volumes', {trigger: true, replace:true});

                    if (Atmo.volumes.length > 0) 
                        Atmo.volumes.select_volume(Atmo.volumes.models[0]);
                    else
                        Atmo.volumes.select_volume(null);

                    Atmo.Utils.notify("Your volume has been destroyed.", "");
                },
				error: function() {
					Atmo.Utils.notify("Volume could not be destroyed", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
				},
            });

        } else if (this.model.get('status') == 'in-use') {
            var instance = Atmo.instances.get(this.model.get("attach_data").instanceId);
            Atmo.Utils.confirm_detach_volume(this.model, instance, {
                success: function() {
                    Atmo.volumes.fetch();
                }
            });
        }

    }
});
