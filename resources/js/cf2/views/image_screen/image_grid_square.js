Atmo.Views.ImageGridSquare = Backbone.View.extend({
    tagName: 'li',
    events: {

    },
    template: _.template(Atmo.Templates.image_grid_square),
    initialize: function() {

    },
    render: function() {
        this.$el
            .html(this.template(this.model.toJSON()))
            .find("img").attr("src", this.model.icon(100))
            .find("a").attr("href", "#images/" + this.model.id);

        return this;
    }
});
