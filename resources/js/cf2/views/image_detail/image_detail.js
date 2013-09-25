Atmo.Views.ImageDetail = Backbone.View.extend({
    className: 'screen image-detail',
    events: {
    },
    template: _.template(Atmo.Templates.image_detail),
    initialize: function(options) {
    },
    render: function() {
        this.$el.html(this.template(this.model.toJSON()));
        return this;
    }
});
