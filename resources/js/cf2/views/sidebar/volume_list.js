Atmo.Views.SidebarVolumeList = Backbone.View.extend({
	initialize: function() {
        this.views = {};
		this.collection.bind('add', this.append_volume, this);
		this.collection.bind('reset', this.render, this);
        this.collection.bind('select', this.highlight, this);
        this.collection.bind('remove', this.remove_volume, this);
    },
	render: function() {
		this.$el.empty();
		var self = this;
        /* performance optimization */
        var frag = document.createDocumentFragment();
		$.each(this.collection.models, function(i,volume) {
            frag.appendChild(self.new_volume_item(volume).el);
		});
        this.$el.append(frag);
	},
    new_volume_item: function(volume) {
        var new_view = new Atmo.Views.SidebarVolumeListItem({model: volume}).render();
        return this.views[volume.id] = new_view;
    },
	append_volume: function(model) {
		this.$el.append(this.new_volume_item(model).el);
	},
    highlight: function(volume) {
        this.$el.find('li').removeClass('active');
        if (volume && this.views[volume.id])
            this.views[volume.id].$el.addClass('active');
    },
	remove_volume: function(model) {
		// This exists in case there is a discrepency between models and the view. More consistent with instance_list.js
        var volume_el = $('li[data-volumeid="' + model.get('id') + '"]');
		if (volume_el.length == 1) {
			var self = this;
			volume_el.find('div').eq(0).slideUp({ complete: function() {
				$(this).parent().remove();
				//self.destroy();
			}});
		}
	}
});
