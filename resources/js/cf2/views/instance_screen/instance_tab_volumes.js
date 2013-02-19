/* Drop down to select a volume to attach & button */
Atmo.Views.InstanceTabVolumes = Backbone.View.extend({
    template: _.template(Atmo.Templates.instance_tab_volumes),
    events: {
        'click li > a': 'swap_volume_status',
    },
    initialize: function() {
        Atmo.volumes.bind('add', this.render, this);
        Atmo.volumes.bind('remove', this.render, this);
        Atmo.volumes.bind('reset', this.render, this);
        Atmo.volumes.bind('attach', this.render, this);
        Atmo.volumes.bind('detach', this.render, this);
    },
    render: function() {

        this.$el.html(this.template());
        var self = this;

        // Don't allow user to fiddle with volumes if instance is shutting-down or terminated.
        if (self.model.get('state_is_delete')) {
            this.$el.find('li').eq(0).remove();
            self.$el.attr('disabled', 'disabled').click(function() { return false; });
            return this;
        }

        var attached_volumes = Atmo.volumes.filter(function(volume) {
            return volume.get('attach_data_instance_id') == self.model.get('id');
        });
        console.log("attached_volumes", attached_volumes);

		console.log("volumes", Atmo.volumes.length);
        var available_volumes = Atmo.volumes.filter(function(volume) {
            return volume.get('status') == 'available';
        });
        console.log("available_volumes", available_volumes);

        if (Atmo.volumes.models.length > 0) {

            // First, get rid of "you have no volumes" text
            this.$el.find('li').eq(0).remove();

            if (available_volumes.length > 0) {
                var available_volumes_title = self.$el.prepend($('<li/>', {
                    'class': 'title',
                    id: 'available_volumes_title',
                    html: 'Available Volumes'
                }));
                $.each(available_volumes, function(i, volume) {
                    self.$el.find('#available_volumes_title').after($('<li/>', {
                        html: '<a href="#" title="Detach Volume"><i class="icon-plus-sign"></i> '+volume.get('name_or_id')+' ('+volume.get('size')+' GB)</a>'
                    }).data('volume', volume));
                });
            }

            if (attached_volumes.length > 0) {
                var attached_volumes_title = self.$el.prepend($('<li/>', {
                    'class': 'title',
                    id: 'attached_volumes_title',
                    html: 'Attached Volumes'
                }));
                $.each(attached_volumes, function(i, volume) {
                    self.$el.find('#attached_volumes_title').after($('<li/>', {
                        html: '<a href="#"><i class="icon-minus-sign"></i> '+volume.get('name_or_id')+' ('+volume.get('size')+' GB)</a>'
                    }).data('volume', volume));
                });
            }

        }

        return this;
    },
    swap_volume_status: function(e) {
        //console.log('attach_volume');
        if (this.model.get('state_is_delete')) {
            $(e.target).addClass("disabled");
            return false;
        }
        else {
            var volume = $(e.target).closest('li').data('volume');


            if (volume.get('status') == 'in-use') {
                // Detach volume
                Atmo.Utils.confirm_detach_volume(volume, this.model);
            }
            else {
                Atmo.Utils.notify('<img src="'+site_root+'/resources/images/loader_bluebg.gif" /> Attaching Volume', '');
				Atmo.Utils.attach_volume(volume, this.model);
            }
        }
    }
});
