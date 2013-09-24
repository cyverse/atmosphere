/* New Instance view */
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
        return this;
    },
    render_image_list: function() {
        console.log(Atmo.images.featured());
        this.$el.find("#machines")
            .append($("<h2>").append("Featured Images"))
            .append(new Atmo.Views.ImageGrid({collection: Atmo.images.featured()}).render().el)
            .append($("<h2>").append("Popular Images"))
            .append($("<h2>").append("Your Images"));
    }
});
