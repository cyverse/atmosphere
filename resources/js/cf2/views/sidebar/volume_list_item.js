Atmo.Views.SidebarVolumeListItem = Backbone.View.extend({
	tagName: 'li',
    className: 'media',
	template: _.template(Atmo.Templates.sidebar_volume_list_item),
	events: {
		'click' : 'vol_clicked',
		'click .rect-delete': 'destroy'
	},
	initialize: function() {
		this.model.bind('destroy', this.remove_volume, this);
        this.model.bind('change:status', this.render, this);
	},
	render: function() {

		// Re-applying the template every time causes the volume list to flash and re-create the list every time.
		if (!this.rendered) {
			this.$el.html(this.template(this.model.toJSON()));
		}

        this.$el.attr('data-volumeid', this.model.get('id'));
        if (this.model.get('status') == 'available') {
            this.$el.find('a.rect-delete').attr("title", "Destroy Volume");
        }
        else {
            this.$el.find('a.rect-delete').attr("title", "Detach Volume");
        }

		var self = this;
		setTimeout(function() {
			self.$el.find('div').slideDown();
		}, 1500);

		this.rendered = true;

		return this;	
	},
	remove_volume: function(model) {
        var volume = $('li[data-volumeid="' + model.get('id') + '"]');
		var self = this;
		volume.find('div').eq(0).slideUp({ complete: function() {
			$(this).parent().remove();
			//self.destroy();
		}});
	},
	vol_clicked: function() {
        Atmo.volumes.select_volume(this.model);
        Backbone.history.navigate('volumes', {trigger: true});
	},
	destroy: function(e) {
		if (e)
			e.stopPropagation();

		var self = this;
		var collection = this.model.collection;
		if (this.model.get('status') == 'in-use') {
            var instance = Atmo.instances.get(this.model.get("attach_data_instance_id"));
            Atmo.Utils.confirm_detach_volume(this.model, instance, {
                success: function() {
                    Atmo.volumes.fetch();
                }
            });
		}
		else {
			this.model.confirm_destroy({
				success: function() {
					Atmo.Utils.notify("Your volume has been destroyed.", "");
				},
				error: function() {
					Atmo.Utils.notify("Could not destroy this volume", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
				},
			});
		}
	}
});
