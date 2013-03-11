Atmo.Views.ResizeInstanceForm = Backbone.View.extend({
	'tagName': 'div',
    'className': 'resize_instance_form',
	template: _.template(Atmo.Templates.resize_instance_form),
	initialize: function() {
	},
	render: function() {
		this.$el.html(this.template(this.model.toJSON()));
		return this;
    }
});
