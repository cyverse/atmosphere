Atmo.Views.ImageSearchForm = Backbone.View.extend({
    template: _.template(Atmo.Templates.image_search_form),
    events: {

    },
    render: function() {
        this.$el.html(this.template());
        return this;
    }
});
