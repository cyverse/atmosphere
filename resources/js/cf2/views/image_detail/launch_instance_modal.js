/**
 * Modal that pops up and lets you launch an instance
 */
Atmo.Views.LaunchInstanceModal = Backbone.View.extend({
    id: 'launch_instance_modal',
    className: 'modal hide fade',
    template: _.template(Atmo.Templates.launch_instance_modal),
	events: {
		'submit form' : 'launch_instance',
        'click .modal-header button' : 'hide'
	},
    initialize: function() {
        this.image = this.options.image;
    },
    hide: function() {
        this.$el.modal('hide');
    },
    render: function() {
        this.$el.html(this.template(this.image.toJSON()));
        this.$el.find(".image-thumb").attr("src", this.image.icon(20));
        return this;
    },
    do_alert: function() {
		var self = this;

        this.$el.modal({
            backdrop: true,
            keyboard: true
        });

        this.$el.modal('show');

        this.$el.find('.modal-footer a').eq(0).click(function() {self.hide();});
    },
	launch_instance: function(e) {
	}
});
