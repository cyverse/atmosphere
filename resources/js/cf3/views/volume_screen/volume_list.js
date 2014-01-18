/**
 * Represents the list of volumes under "available volumes" on the
 * volume screen
 */
define(['backbone', 'templates', 'jquery-ui', 'views/volume_screen/volume'], function(Backbone, Templates, jqui, VolumeScreenVolume) {

var DraggableVolumes = Backbone.View.extend({
    template: _.template(Templates.volume_screen_volumes),
    initialize: function(options) {
        this.volumes = options.volumes;
        this.instances = options.instances;
        this.volumes.bind("add", this.append_volume, this);
        this.volumes.bind('change:status', this.status_changed, this);
        this.volumes.bind('remove', this.volume_removed, this);
        this.$container = null;
        this.volume_map = {};   // maps a volume_id (string) to a view of type VolumeScreenVolume
    },
    append_volume: function(volume) {

        // Make sure this volume isn't a duplicate
        if (!this.volume_map[volume.get('id')]) {
            var new_view = new VolumeScreenVolume({model: volume});
            if (_.keys(this.volume_map).length == 0)
                this.$el.find('#draggable_volume_list span').remove();
            this.volume_map[volume.get('id')] = new_view;
            this.$container.append(new_view.render().el);
        }
    },
    status_changed: function(volume) {
        if (volume.get('status') == 'available') {
            this.append_volume(volume);
        }
        else if (volume.get('status') == 'in-use' || volume.get('status') == 'attaching') {
            this.volume_map[volume.get('id')] && this.volume_map[volume.get('id')].remove();
            this.volume_removed(volume);

        }
    },
    volume_removed: function(volume) {
        delete this.volume_map[volume.get('id')];
        if (_.keys(this.volume_map).length == 0)
            this.$container.html("<span>No available volumes.</span>");
    },
    render: function() {
        //console.log("render volume screen volumes");
        this.$el.html(this.template());
        this.$container = this.$el.find('#draggable_volume_list');    
        
        var self = this;

        var available_volumes = this.volumes.get_available();
        if (available_volumes.length > 0) {
            self.$container.empty();
            $.each(available_volumes, function(i, volume) {
                self.append_volume(volume);
            });
        }

        this.$el.find('#draggable_volume_list').droppable({
            accept: '.attached',
            hoverClass: 'droppable-highlight',
            drop: function(event, ui) {
                var volume = $(ui.draggable).data('volume');
                var instance_id = volume.attributes.attach_data_instance_id;
                var instance = this.instances.get(instance_id)
                Atmo.Utils.confirm_detach_volume(volume, instance, {
                    success: function() {
                        Atmo.volumes.fetch();
                        console.log('success - volume_list')
                    }
                });
                //$(ui.draggable).remove();
            }
        });

        return this;
    }
});

return DraggableVolumes;

});
