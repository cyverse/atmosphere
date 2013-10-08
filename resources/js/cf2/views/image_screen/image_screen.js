Atmo.Views.ImageScreen = Backbone.View.extend({
    tagName: 'div',
    className: 'screen',
    id: 'imageStore',
    events: {
    },
    template: _.template(Atmo.Templates.image_screen),
    initialize: function(options) {
		Atmo.images.bind('reset', this.render_image_list, this);
    },
    render: function() {
        this.$el.html(this.template());
        this.render_image_list();
        new Atmo.Views.ImageSearchForm({el: this.$el.find('#image_search_form_container')[0] }).render();
        return this;
    },
    render_image_list: function() {
        if (Atmo.images.isEmpty())
            return;
        this.$el.find("#machines")
            .append($("<h2>").append("Featured Images"))
            .append(new Atmo.Views.ImageGrid({collection: Atmo.images.get_featured()}).render().el)
            .append($("<h2>").append("Popular Images"))
            .append($("<h2>").append("Your Images"));
    }
});
