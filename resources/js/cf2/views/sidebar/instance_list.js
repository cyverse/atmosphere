Atmo.Views.SidebarInstanceList = Backbone.View.extend({
	initialize: function() {
		this.collection.bind('reset', this.render, this);
		this.collection.bind('add', this.append_instance, this);
        this.collection.bind('remove', this.remove_instance, this);
	},
	render: function() {
		var self = this;

		// Instead of simply emptying the list, we should see what it contains, and then animate accordingly.
		this.$el.empty();

        /* performance optimization */
        var frag = document.createDocumentFragment();
		$.each(this.collection.models, function(i, instance) {
            frag.appendChild(self.new_instance_item(instance).el);
		});
        this.$el.append(frag);
	},
	append_instance: function(model) {
		this.$el.append(this.new_instance_item(model).el);
	},
    new_instance_item: function(model) {
        return new Atmo.Views.SidebarInstanceListItem({model: model}).render();
    },
    remove_instance: function(model) {
        var instance = this.$el.find('li[data-instanceid="' + model.get('id') + '"]');
		instance.find('div').eq(0).slideUp({ complete: function() {
			$(this).parent().remove();
		}});
    }
});
