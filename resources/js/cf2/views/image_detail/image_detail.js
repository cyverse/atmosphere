Atmo.Views.ImageDetail = Backbone.View.extend({
    className: 'screen image-detail',
    events: {
        'click .launch-instance-btn': 'show_modal'
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
            .find('.image-big-icon').attr('src', this.model.icon(200)).end()
            .find('.media-body').append(tagger.render().el);
        return this;
    },
    show_modal: function(e) {
        var modal = new Atmo.Views.LaunchInstanceModal({image: this.model});
        modal.render().$el.appendTo('body');
        modal.do_alert();
        return false;
    }
});
