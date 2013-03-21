Atmo.Views.AlertModal = Backbone.View.extend({
    id: 'alert_modal',
    className: 'modal hide fade',
    template: _.template(Atmo.Templates.alert_modal),
    initialize: function() {
        
    },
    render: function() {
        this.$el.html(this.template());
        return this;
    },
    do_alert: function(header, body, options) {
        // Displays a modal which has 'Header' and 'Body' text

        // Options: { on_cancel: function, on_confirm: function }
        $('#alert_modal').modal({
            backdrop: true,
            keyboard: true
        });

        $('#alert_modal .modal-header h2').html(header);
        $('#alert_modal .modal-body p').html(body);

        $('#alert_modal .modal-header button').click(function() {
            $('#alert_modal').modal('hide');
        });

        $('#alert_modal').modal('show');

        $('#alert_modal .modal-footer a').unbind('click');

        var button_listener = function(callback) {
            return function(e) {
                e.preventDefault();
                $('#alert_modal').modal('hide');
                $('.modal-backdrop').remove();
                if (callback != undefined) 
                    callback();
                $(window).unbind('keyup');
            }
        }

        $(window).on('keyup', function(e) {

            // Only confirm if user does not have cursor in a textarea
            if (e.keyCode == 13 && $('textarea:focus').length == 0) {
                $('#alert_modal .modal-footer a').eq(1).trigger('click');
            }
        });

        if (options != undefined && options.ok_button != undefined)
            $('#alert_modal .modal-footer a').eq(1).html(options.ok_button);
        else
            $('#alert_modal .modal-footer a').eq(1).html("Ok");
        
        $('#alert_modal .modal-footer a').show();
        $('#alert_modal .modal-footer a').eq(0).click(button_listener(options.on_cancel));
        $('#alert_modal .modal-footer a').eq(1).click(button_listener(options.on_confirm));
    }
});
