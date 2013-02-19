Atmo.Views.NotificationHolder = Backbone.View.extend({
    initialize: function() {
        Atmo.notifications.bind('add', this.add_notification, this);
    },
    add_notification: function(model) {
        var x_close = $('<button/>', {
            type: 'button',
            'class': 'close',
            'data-dismiss' : 'alert',
            html: '&times'
        });
        var alert_el = $('<div/>', {
            'class': 'alert alert-info fade in',
            html: '<strong>' + model.get('header') + '</strong> ' + model.get('body')

        });
        this.$el.html(alert_el.prepend(x_close));

        // Automatically dismiss alert after 5 seconds
        if (model.get('sticky') == false) {
            setTimeout(function() {
                x_close.trigger('click');
            }, 10*1000);
        }
    }
});
