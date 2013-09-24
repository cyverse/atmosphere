Atmo.Views.ImageGrid = Backbone.View.extend({
    id: 'image-grid',
    tagName: 'ul',
    events: {

    },
    initialize: function() {

    },
    render: function() {
        var self = this;
        this.collection.each(function(m) {
            self.$el.append(new Atmo.Views.ImageGridSquare({model: m}).render().el); 
        });
        return this;
    }
});
