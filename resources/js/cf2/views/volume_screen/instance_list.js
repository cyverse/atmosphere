/**
 * Represents the list of instances under "running instances" on the volume screen
 */
Atmo.Views.VolumeScreenDraggableInstances = Backbone.View.extend({
    'tagName': 'div',
    template: _.template(Atmo.Templates.volume_screen_instances),
    initialize: function() {
        this.instance_map = {}; // maps instance_id (string) to Atmo.Views.VolumeScreenInstance
        this.volume_map = {};   // maps volume_id (string) to Atmo.Views.VolumeScreenVolume

        Atmo.volumes.bind('change:status', this.volume_status_changed, this);
        Atmo.volumes.bind('remove', this.remove_volume, this);

        Atmo.instances.bind('change:state', this.instance_state_changed, this);
        Atmo.instances.bind('remove', this.remove_instance, this);
    },
    remove_volume: function(volume) {
        this.volume_map[volume.get('id')] && this.volume_map[volume.get('id')].remove();
        delete this.volume_map[volume.get('id')];
    },
    volume_status_changed: function(volume) {
        // if the volume is now in use, append it to the appropriate instance list.
        // if the volume is now available, get rid of it's representation here
        if (volume.get('status') == 'attaching' || volume.get('status') == 'detaching' || volume.get('status') == 'in-use') {
            if (!this.volume_map[volume.get('id')]) {
                new_view = new Atmo.Views.VolumeScreenVolume({model: volume});
                this.volume_map[volume.get('id')] = new_view;
                if (this.instance_map[volume.get('attach_data_instance_id')] !== undefined) {
                    this.instance_map[volume.get('attach_data_instance_id')].append_volume(new_view);
                }
            }
        } else if (volume.get('status') == 'available') {
            this.remove_volume(volume);
        }
    },
    new_instance_item: function(instance) {
        var new_view = new Atmo.Views.VolumeScreenInstance({model: instance});
        this.instance_map[instance.get('id')] = new_view;
        return new_view.render().el;
    },
    instance_state_changed: function(instance) {
		if (instance.get('state_is_active')) {
		
			// If this is the first instance a user has, must remove "No Running Instances" text before appending new instance list item.
			if (this.$el.find('#draggable_instance_list').children().length == 0) {
				this.$el.find('#draggable_instance_list').html("");
			}

			this.$el.find('#draggable_instance_list').append(this.new_instance_item(instance));
		}
		else 
			this.remove_instance(instance);
    },
    remove_instance: function(instance) {
        this.instance_map[instance.get('id')] && this.instance_map[instance.get('id')].remove();
        delete this.instance_map[instance.get('id')];
        // call update in case volumes need to be freed
        Atmo.volumes.update();
    },
    render: function() {
        this.$el.html(this.template());

        var self = this;
        var running_instances = 0;
    
        var instance_list = this.$el.find('#draggable_instance_list');

        $.each(Atmo.instances.models, function(i, instance) {
            if (instance.get('state_is_active')) {
                running_instances++;

                var instance_list_item = self.new_instance_item(instance);

                if (running_instances == 1)
                    instance_list.html(instance_list_item);
                else
                    instance_list.append(instance_list_item);
            }
        });

        var self = this;

        // Now that all the instance list items have been created, append all the attached volumes to their instances
        $.each(Atmo.volumes.models, function(i, volume) {
            if (volume.get('status') == 'in-use' || volume.get('status') == 'detaching') {
                //TODO: If we are in the detaching state we should poll until we change states..
                var new_view = new Atmo.Views.VolumeScreenVolume({model: volume});
                self.volume_map[volume.get('id')] = new_view;
                instance_id = volume.get('attach_data').instanceId;
                if (self.instance_map[instance_id] !== undefined) {
                  self.instance_map[instance_id].append_volume(new_view);
                }
            }
        });

    }
});
