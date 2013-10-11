Atmo.Views.ImageGridSquare = Backbone.View.extend({
    tagName: 'li',
    className: 'media',
    events: {
        'click a': 'select_image'
    },
    template: _.template(Atmo.Templates.image_grid_square),
    initialize: function() {
    },
    render: function() {
        this.$el
            .html(this.template(this.model.toJSON()))
            .find("img").attr("src", this.model.icon(100)).end()
            .find("a").attr("href", "#images/" + this.model.id);

        return this;
    },
    select_image: function(e) {
        Atmo.images.select_machine(this.model);
        return false;
    }
});
