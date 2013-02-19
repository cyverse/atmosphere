/* A single image as disapled on the 'create instance' view sidebar */
Atmo.Views.ImageListItem = Backbone.View.extend({
	tagName: 'li',
	template: _.template(Atmo.Templates.image_list_item),
	initialize: function() {
		this.$el.data('image', this.model);
	},
	render: function() {
		this.$el.html(this.template(this.model.toJSON()));
	
		var self = this;
		$.each(this.model.get('tags'), function(i, e) {
			$('<li>')
				.html('<a>'+e+'</a>')
				.appendTo(self.$el.find('.tag_list'));
		});

		this.$el.attr('data-tags', this.model.get('tags').join(' '));
		return this;
	}
});	
