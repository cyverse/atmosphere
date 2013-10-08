/**
 * Modal that pops up and lets you launch an instance
 */
Atmo.Views.LaunchInstanceModal = Backbone.View.extend({
    id: 'launch_instance_modal',
    className: 'modal hide fade',
    template: _.template(Atmo.Templates.launch_instance_modal),
	events: {
		'submit form' : 'launch_instance',
        'click .modal-header button' : 'hide',
        'click .modal-footer .btn-primary' : 'submit_form'
	},
    initialize: function() {
        this.image = this.options.image;
    },
    hide: function() {
        this.$el.modal('hide');
    },
    render: function() {
        this.$el
            .html(this.template(this.image.toJSON()))
            .find(".image-thumb").attr("src", this.image.icon(20));
        new Atmo.Views.InstanceSizeDropdown({el: this.$el.find("#instance_size")[0]}).render();

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
    submit_form: function(e) {
        /* trigger the submit event on the form when the button is clicked */
        this.$el.find('form').submit();
        return false;
    },
    get_form_data: function() {
        /* get form data as object */
        var form_data = this.$el.find('form').serializeArray();
        return _.object(_.map(form_data, function(x) {
            return [x.name, x.value]; 
        }));
    },
	launch_instance: function(e) {
        var form_data = this.get_form_data();
        _.extend(form_data, {
            'machine_alias': this.image.id
        });
        console.log(form_data);
        // TODO: validation

        var self = this;
        var instance = new Atmo.Models.Instance();
        instance.save(form_data, {
            wait: true,
            success: function(model) {
                Atmo.instances.update({success: function() {
				    Atmo.instances.get(model.id).select();
                }});
				window.app.navigate('instances', {trigger: true, replace: true});
                Atmo.Utils.notify("Instance Launched", "Your instance will be ready soon.");

                self.$el.modal('hide');
            },
            error: function() {
				Atmo.Utils.notify("Instance launch was unsuccessful", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
                self.$el.modal('hide');
            }
        });
        return false;
	}
});
