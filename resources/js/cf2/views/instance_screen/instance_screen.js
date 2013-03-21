/* Instance views */
Atmo.Views.InstanceScreen = Backbone.View.extend({
	tagName: 'div',
	className: 'screen',
	id: 'instanceList',
	template: _.template(Atmo.Templates.instance_screen),
	alt_template: _.template(Atmo.Templates.instance_screen_alt),
	events: {
		'click .terminate_instance': 'terminate',
	},
	initialize: function(options) {
		Atmo.instances.bind('reset', this.render, this);
		Atmo.instances.bind('add', this.append_instance, this);
        Atmo.instances.bind('remove', this.remove_instance, this);
        Atmo.instances.bind('select', this.select_instance, this);
	},
	render: function() {
		if (Atmo.instances.models.length > 0) {

			if (this.$el.find('#resource_usage_holder').length == 0)
				this.$el.html(this.template());
			
			this.mem_resource_chart = new Atmo.Views.ResourceCharts({
				el: this.$el.find('#memHolder'),
				quota_type: 'mem'
			}).render();
			this.cpu_resource_chart = new Atmo.Views.ResourceCharts({
				el: this.$el.find('#cpuHolder'),
				quota_type: 'cpu'
			}).render();

			if (Atmo.instances.models.length > 0) {
				var self = this;
                
                /* performation optimization */
                var frag = document.createDocumentFragment();
				$.each(Atmo.instances.models, function(k, v) {
					frag.appendChild(self.new_instance_tabs_holder(v).el);
				});
                this.$el.append(frag);
			}

		} else {
			this.$el.html(this.alt_template());
		}

        // Assign content to the popovers
        this.$el.find('#help_resource_usage').popover({
            placement: 'bottom',
            title: 'My Resource Usage <a class="close" data-dismiss="popover" href="#instances" data-parent="help_resource_usage">&times</a>',
            html: true,
            content: function() {
                var content = 'Your "resource usage" is determined by how many CPUs and GB of memory your instances are using cumulatively. <br /><br />';
                content += 'You can re-use your resources only after you\'ve terminated an instance and it has disappeared from the "My Instances" list on the left.';
                return content;
            }
        }).click(_.bind(this.x_close, this));

        this.$el.find('#help_request_more_resources').popover({
            placement: 'left',
            html: true,
            title: 'Request More Resources <a class="close" data-dismiss="popover" href="#instances" data-parent="help_request_more_resources">&times</a>',
            content: function() {
                var content = '<form name="request_more_resources"><input type="hidden" name="username" value="'+Atmo.profile.get('id')+'">';
                content += 'Requested Resources: <textarea name="quota" placeholder="E.g. 4 CPUs and 8 GB memory, enough for a c1.medium, etc."></textarea><br />';
                content += 'Reason you need these resources: <textarea name="reason" placeholder="E.g. To run a program or analysis, store larger output, etc. "></textarea><Br /><input type="submit" value="Request Resources" class="btn" id="submit_resources_request"></form>';
                return content;
            }
        }).click(_.bind(this.x_close, this));


		return this;
	},
    submit_resources_request: function(e) {
            e.preventDefault();

            // Make sure they filled out both fields
            var valid = true;

            $('form[name="request_more_resources"] span').remove();

            if ($('textarea[name="quota"]').val().length == 0) {
                valid = false;
                $('textarea[name="quota"]').before('<span style="color: #B94A48">(Required)</span>');
            }
            if ($('textarea[name="reason"]').val().length == 0) {
                valid = false;
                $('textarea[name="reason"]').before('<span style="color: #B94A48">(Required)</span>');
            }
                
            if (valid) {

                var self = this;
                $.ajax({
                    type: 'POST',
                    url: site_root + '/api/request_quota/', 
                    data: $('form[name="request_more_resources"]').serialize(),
                    success: function() {
                        $('#submit_resources_request').val("Request Submitted!").attr("disabled", "disabled").click(function() { return false; });
						setTimeout(function() {
							$('#help_request_more_resources').click();
						}, 1000);
                    },
                    dataType: 'text'
                });
            }
            return false;
    },
    x_close: function() {
            /**
             * Deareset Ms. Monica Lent,
             * 
             * This callback function was assigned to the "Request More Resources" button (henceforth referred to as the link trigger)
             * by means of _.bind(this.x_cose, this) which guarantees that references to 'this' from within this function refer to the
             * view.  If you really needed to access the link trigger element, you could do so by allowing this element to accept an 
             * event object e, and using $(e.currentTarget).  Furthermore, to assign the submit_resources_request() callback to the click
             * event of #submit_resources_request, we again use our friend _.bind() to ensure that 'this' inside submit_resources_request()
             * refers to the view instead of #submit_resources_request.
             *
             * Love,
             * Backbone.js
            */
            $('#submit_resources_request').click(_.bind(this.submit_resources_request, this));

            // Must assign this function after the popover is actually rendered, so we find '.close' element
            $('.close').click(function(e) {
                e.preventDefault();
                var popover_parent = $(e.currentTarget).data('parent');
                if (popover_parent != undefined) {
                    $('#'+popover_parent).popover('hide');
                }            
            });
	},
	append_instance: function(model) {
		if (this.$el.find('#instance_holder').length == 0)
			this.render();
		else { 
            this.new_instance_tabs_holder(model).$el.appendTo(this.$el.find('#instance_holder'));
            this.cpu_resource_chart.render();
            this.mem_resource_chart.render();
        }
	},
    new_instance_tabs_holder: function(model) {
        var new_view = new Atmo.Views.InstanceTabsHolder({model: model}).render();
        new_view.$el.css('display', 'none');
        return new_view;
    },
    remove_instance: function(model) {
        this.$el.find('.instance_tabs_holder[data-instanceid="'+model.get('id')+'"]').remove();
        this.cpu_resource_chart.render();
        this.mem_resource_chart.render();
        if (Atmo.instances.isEmpty())
            this.$el.html(this.alt_template());
    },
	terminate: function(e) {
		Atmo.instances.selected_instance.confirm_terminate({
			success: function() {
				Atmo.instances.update();

				var header = "Instance Terminated";
				var body = "Your instance is shutting down.";
				Atmo.Utils.notify(header, body);

			},
			error: function(model, message) {
				//console.log('error');
				//console.log(model, message);
			}
		});
	}
});
