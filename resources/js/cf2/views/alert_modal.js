/**
 *
 * Base view for alert modals used throughout the application.
 * To initialize and show, render and call 'do_alert' with header and body parameters and options.
 *
 */

Atmo.Views.AlertModal = Backbone.View.extend({
    id: 'alert_modal',
    className: 'modal fade',
    template: _.template(Atmo.Templates.alert_modal),
    initialize: function() {
        
    },
    render: function() {
        this.$el.html(this.template());
        return this;
    },
    do_alert: function(header, body, options) {

        /* Options:
			on_confirm: Function to execute if user confirms modal.
			on_cancel: If user cancels.
			ok_button: Alternate text for 'ok' button on modal. 
		*/

        $('#alert_modal').modal({
            backdrop: true,
            keyboard: true
        });

        $('#alert_modal .modal-header h2').html(header);
        $('#alert_modal .modal-body p').html(body);

		// User clicks the 'x' button in the modal header
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

		// Allow user to hit enter to confirm
        $(window).on('keyup', function(e) {
            // Only confirm if user does not have cursor in a textarea
            if (e.keyCode == 13 && $('textarea:focus').length == 0) {
                $('#alert_modal .modal-footer a').eq(1).trigger('click');
            }
        });

        if (options != undefined && options.cancel_button != undefined)
            $('#alert_modal .modal-footer a').eq(0).html(options.cancel_button);
        else
            $('#alert_modal .modal-footer a').eq(0).html("Cancel");

        if (options != undefined && options.ok_button != undefined)
            $('#alert_modal .modal-footer a').eq(1).html(options.ok_button);
        else
            $('#alert_modal .modal-footer a').eq(1).html("Ok");
        
        $('#alert_modal .modal-footer a').eq(0).click(button_listener(options.on_cancel));
        $('#alert_modal .modal-footer a').eq(1).click(button_listener(options.on_confirm));
    }
});
