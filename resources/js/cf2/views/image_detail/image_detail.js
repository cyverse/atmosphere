Atmo.Views.ImageDetail = Backbone.View.extend({
    className: 'screen image-detail',
    events: {
    },
    template: _.template(Atmo.Templates.image_detail),
    initialize: function(options) {
    },
    render: function() {
        var tagger = new Atmo.Views.Tagger({
            default_tags: this.model.get('tags'),
            editable: false
        });

        this.$el
            .html(this.template(this.model.toJSON()))
            .find('.img img').attr('src', this.model.icon(200)).end()
            .find('.bd').append(tagger.render().el);
        return this;
    }
});
