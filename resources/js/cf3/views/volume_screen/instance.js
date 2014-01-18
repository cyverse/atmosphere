/**
 * Represents a single instance on the volume screen
 */
Atmo.Views.VolumeScreenInstance = Backbone.View.extend({
    tagName: 'li',
    append_volume: function(volume_view) {
        this.$el.find('ul').append(volume_view.render().el);
    },
    render: function() {
        this.$el
            .html('<img class="image_icon" src="' + this.model.get('image_url') + '" height="30" width="30" /><strong>' 
                + this.model.get('name_or_id') + '</strong><br />' + this.model.get('public_dns_name') 
                + '<br /><h3>Attached Volumes:</h3><ul />')
            .data('instance', this.model);

        // Make this element droppable
        this.$el.droppable({
            hoverClass: 'droppable-highlight',
            accept: '.unattached',
            drop: _.bind(this.on_drop, this)
        });

        return this;
    },
    on_drop: function(event, ui) {

        var self = this;

        // Get volume model
        var volume = $(ui.draggable).data('volume');

        // Check if volume is in use: this should never happen
        if (volume.get('status') == 'in-use') 
            Atmo.Utils.notify("ERROR", "Volume is not ready. Please refresh and try again.");
        else {
            Atmo.Utils.attach_volume(volume, this.model, null);
            $(ui.draggable).remove();
        };
    }
});
