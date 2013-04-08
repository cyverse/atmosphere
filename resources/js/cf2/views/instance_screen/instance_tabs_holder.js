/**
 *
 * Provides instance's details, determines shell/vnc availability, and displays shell/vnc.
 *
 */
Atmo.Views.InstanceTabsHolder = Backbone.View.extend({
	tagName: 'div',
	className: 'instance_tabs_holder',
	template: _.template(Atmo.Templates.instance_tabs_holder),
	events: {
		'click a.instance_shell_tab': 'open_shell',
		'click a.instance_vnc_tab': 'open_vnc',
		'click .terminate_shell': 'close_shell',
		'click .terminate_vnc': 'close_vnc',
		'click .request_imaging_btn': 'request_imaging',
		'click .report_instance_btn': 'report_instance',
		'click .resize_instance_btn' : 'resize_instance',
		'change select[name="vis"]': 'toggle_vis_input',
		'click .editing': 'edit_instance_info',
		'click .editable' : 'redir_edit_instance_info',
        'click a.instance_info_tab' : 'redraw_instance_graph',
		'click .btn.suspend_resume_instance_btn' : 'suspend_resume_instance'
	},
	initialize: function(options) {
		this.model.bind('change:running_shell', this.open_or_close_frames, this);
		this.model.bind('change:running_vnc', this.open_or_close_frames, this);
		this.model.bind('change:state', this.instance_info, this);
		this.model.bind('change:ip_address', this.instance_info, this);
		this.model.bind('change:launch_relative', this.instance_info, this);
        this.model.bind('change:has_shell, change:has_vnc', this.update_shell_vnc_tabs, this);
		Atmo.instances.bind('select', this.select_instance, this);
        this.rendered = false;
	},
    update_shell_vnc_tabs: function() {
        var self = this;
		//if (this.model.get('state') != 'pending') {
            // if shell is available, show it. Otherwise, disable it
            if (this.model.get('state_is_active') && this.model.get('has_shell') == true) {
                this.$el.find('.instance_tabs a.instance_shell_tab')
                    .show()
                    .removeClass("tab_disabled")
                    .attr("title", "");
                
                // Get rid of tooltip and 'Shell Unavailable' text
                this.$el.find('.instance_tabs a.instance_shell_tab').html("Access by Shell");
                this.$el.find('.instance_tabs a.instance_shell_tab i').remove();
            } else if (this.model.get('has_shell') == false || this.model.get('has_shell') == undefined) {
                this.$el.find('.instance_tabs a.instance_shell_tab')
                    .addClass("tab_disabled")
                    .attr("title", "This instance does not support shell.");

                // Give you user reasons it might be disabled
                this.$el.find('.instance_tabs a.instance_shell_tab').html('Shell Unavailable');

                var shell_help = $('<a/>', {
                    class: 'context-helper',
                    id: 'help_no_shell_'+self.model.get('id'),
                    html: '<i class="icon-question-sign"></i>'
                }).popover({
                    title: 'Shell Unavailable <a class="close" data-dismiss="popover" href="#instances" data-parent="help_no_shell_'+self.model.get('id')+'">&times</a>',
                    html: true,
                    content: function() {
                        var content = 'The web-based shell may be unavailable for several reasons: <ul>';
                        content += '<li> Instance is pending, shutting down, or terminated.</li>';
                        content += '<li> Instance is based on an old image and does not support web shell. Try launching a newer version or connect using Terminal or PuTTY. (<a href="https://pods.iplantcollaborative.org/wiki/x/Oqxm#LoggingIntoanInstance-LoggingintoaninstancewithSSH" target="_blank">Learn How</a>)</li> ';
                        content += '<li> Instance was corrupted during launch. This happens from time to time. Try terminating the instance and launching a new one.</li>';
                        content += '</ul>';
                        return content;
                    },
                    placement: 'bottom'
                }).click(this.x_close);

                this.$el.find('.instance_tabs a.instance_shell_tab').append(shell_help);
            }

            // same for vnc
            if (this.model.get('state_is_active') && this.model.get('has_vnc') == true) {
                this.$el.find('.instance_tabs a.instance_vnc_tab')
                    .show()
                    .removeClass("tab_disabled")
                    .attr("title", "");

                // Get rid of tooltip and 'VNC Unavailable' text
                this.$el.find('.instance_tabs a.instance_vnc_tab').html("Access by VNC");
                this.$el.find('.instance_tabs a.instance_vnc_tab i').remove();
            } else if (this.model.get('has_vnc') == false || this.model.get('has_vnc') == undefined) { 
                this.$el.find('.instance_tabs a.instance_vnc_tab')
                    .addClass("tab_disabled")
                    .attr("title", "This instance does not support VNC");
                
                // Give you user reasons it might be disabled
                this.$el.find('.instance_tabs a.instance_vnc_tab').html('VNC Unavailable');

                var vnc_help = $('<a/>', {
                    class: 'context-helper',
                    id: 'help_no_vnc_'+self.model.get('id'),
                    html: '<i class="icon-question-sign"></i>'
                }).popover({
                    title: 'VNC Unavailable <a class="close" data-dismiss="popover" href="#instances" data-parent="help_no_vnc_'+self.model.get('id')+'">&times</a>',
                    html: true,
                    content: function() {
                        var content = 'VNC may be unavailable for several reasons: <ul>';
                        content += '<li> Instance is pending, shutting down, or terminated.</li>';
                        content += '<li> Instance does not support VNC because it does not have a desktop interface. You can still access it by shell, however.</li>';
                        content += '<li> Instance was corrupted during launch. This happens from time to time. Try terminating the instance and launching a new one.</li>';
                        content += '</ul>';
                        content += 'To guarantee VNC access, launch from an image tagged with "VNC". Do this by searching for <em>tag:vnc</em>.';
                        return content;
                    },
                    placement: 'bottom'
                }).click(this.x_close);

                this.$el.find('.instance_tabs a.instance_vnc_tab').append(vnc_help);
            }
		//}
    },
	render: function() {
		this.$el.html(this.template(this.model.toJSON()));

		this.$el.data('instance', this.model);
		this.$el.attr('data-instanceid', this.model.get('id'));
		var self = this;
		this.$el.find('.instance_tabs a.instance_shell_tab, .instance_tabs a.instance_vnc_tab').addClass("tab_disabled");

        this.update_shell_vnc_tabs();

		// Display 'Request Imaging' tab if they've already clicked the button for this instance before	
		if (this.$el.find('.module[data-ip="'+this.model.get('public_dns_name')+'"]').length != 0)
			this.$el.find('a.request_imaging').fadeIn('fast');
		else
			this.$el.find('a.request_imaging').fadeOut('fast');

		this.display_close_buttons();


		return this;
	},
    x_close: function(e) {
            $('.close').click(function(e) {
                e.preventDefault();
                var popover_parent = $(e.currentTarget).data('parent');
                if (popover_parent != undefined) {
                    $('#'+popover_parent).popover('hide');
                }            
            });
    },
    redraw_instance_graph: function() {
        if (this.instance_graph)
            this.instance_graph.draw();
    },
	select_instance: function(model) {
          if (model == this.model) {
			  if (this.rendered) {
				  this.redraw_instance_graph();
			  } else {
				  this.instance_info();
				  this.rendered = true;
			  }
			  this.$el.show();
		  } else {
			this.$el.hide();
		  }
	},
	display_close_buttons: function() {
		this.$el.find('.terminate_shell').remove();	
		if (this.model.get('running_shell'))
			this.add_close_shell(this.model);

		this.$el.find('.terminate_vnc').remove();	
		if (this.model.get('running_vnc'))
			this.add_close_vnc(this.model);
	},
    display_graph: function() {
		//this.$el.find('.instance_graph').css({width: '600px', height: '200px'});

        // do not try to display instance graphs for IE lte 8.  D3 does not support old browsers.
        if ($.browser.msie && parseInt($.browser.version, 10) <= 8)
            this.$el.find('.instance_graph').html('Your browser does not support the features necessary to display instance metrics graphs. Please <a href="http://windows.microsoft.com/en-us/internet-explorer/products/ie/home">upgrade</a> to the lastest version or use <a href="https://google.com/chrome">another browser</a>.');
        else {
		    this.$el.find('.instance_graph');
		    this.instance_graph = new Atmo.Views.InstanceGraph({model: this.model, el: this.$el.find('.instance_graph')}).render();
        }
    },
	instance_info: function() {
		this.$el.find('.instance_info').html(_.template(Atmo.Templates.instance_info_tab, this.model.toJSON()));

		var self = this;

        this.display_graph();

		// Disable if instance is not running
		if (!this.model.get('state_is_active')) {
			this.$el.find('.request_imaging_btn').addClass('disabled').attr('disabled', 'disabled');
			this.$el.find('.resize_instance_btn').addClass('disabled').attr('disabled', 'disabled');
			this.$el.find('.report_instance_btn').addClass('disabled').attr('disabled', 'disabled');
			this.$el.find('.suspend_resume_instance_btn').addClass('disabled').attr('disabled', 'disabled');
			this.$el.find('#instance_tabs a[href="#instance_shell"]').addClass("tab_disabled");
			this.$el.find('#instance_tabs a[href="#instance_vnc"]').addClass("tab_disabled");
		}

		if (this.model.get('state_is_inactive'))
			this.$el.find('.terminate_instance').addClass('disabled').attr('disabled', 'disabled');

		// Shutting-down/terminted instances should have terminate button disabled
		if (this.model.get('state_is_delete')) {
			this.$el.find('.terminate_instance').addClass('disabled').attr('disabled', 'disabled');
			this.$el.find('.suspend_resume_instance_btn').addClass('disabled').attr('disabled', 'disabled');

		}

		// Display OpenStack-specific options
		if (Atmo.profile.get('selected_identity').get('provider_id') == 2) {
			this.$el.find('.btn.resize_instance_btn').fadeIn('fast');
			if (this.model.get('state') == 'suspended') {
				this.$el.find('.btn.suspend_resume_instance_btn').html('<i class="icon-play"></i> Resume').removeClass('disabled').removeAttr('disabled');
			}
			else {
				this.$el.find('.btn.suspend_resume_instance_btn').fadeIn('fast');
			}
		}
		else {
			this.$el.find('.btn.resize_instance_btn').hide();
			this.$el.find('.btn.suspend_resume_instance_btn').hide();
		}


		// Make the tags pretty
		if (this.model.get('tags').length > 0) 
			var tags_array = this.model.get('tags');
		else 
			var tags_array = [];

        var tagger = new Atmo.Views.Tagger({
            default_tags: tags_array,
            change: function(tags) {
                self.model.save({tags: tags}, {patch: true});
            },
            duplicate_rejected: function(tag) {
                var header = "You cannot add this tag";
                var body = "Your instance <strong>" + self.model.get('name_or_id') + "</strong> is already tagged with <strong>" + tag.trim() + "</strong>";
                Atmo.Utils.notify(header, body);
            }
        });

        this.$el.find('#instance_tags').append(tagger.render().el);

        // enable editing if the instance isn't shutting down or terminated
		if (!self.model.get('state_is_delete')) {
            $.each(this.$el.find('.editable'), function(i, el) {
				$(el).append($('<span/>', {
					html: 'Edit Name',
					'class': 'editing'
				}));
            });

            tagger.set_editable(true);
		}

		resizeApp();
	},
	open_shell: function(e) {
		e.preventDefault();
		if (this.model.get('has_shell')) { 
			this.model.set('running_shell', true);
			this.$el.find('.shell_iframe').hide();
			var ipaddr = this.model.get('public_dns_name');
			this.$el.find('.shell_iframe[data-ip="'+ipaddr+'"]').fadeIn('fast');
			resizeApp();
		} else {
			return false;
		}
	},
	open_vnc: function(e) {
		e.preventDefault();
		if (this.model.get('has_vnc')) {
			this.model.set('running_vnc', true);
			this.$el.find('.vnc_iframe').hide();
			var ipaddr = this.model.get('public_dns_name');
			this.$el.find('.vnc_iframe[data-ip="'+ipaddr+'"]').fadeIn('fast');
			resizeApp();
		} else {
			return false;
		}
	},
	close_shell: function(e) {
		e.stopPropagation();
		e.preventDefault();
		this.model.set('running_shell', false);
	},
	close_vnc: function(e) {
		e.stopPropagation();
		e.preventDefault();
		this.model.set('running_vnc', false);
	},
	open_or_close_frames: function() {

		if (this.model.get('running_shell'))
			this.instance_shell();
		else
			this.terminate_shell();

		if (this.model.get('running_vnc'))
			this.instance_vnc();
		else 
			this.terminate_vnc();

		this.display_close_buttons();
	},
	instance_shell: function() {

		var ipaddr = this.model.get("public_dns_name");
		
		if (this.$el.find('.instance_tabs a[href="#instance_shell"]').hasClass("tab_disabled")) {
			return false;
		} else {
			var currentShell = this.$el.find('.shell_iframe[data-ip="'+ipaddr+'"]');
			if (currentShell.length == 0) {	
				this.$el.find('.shell_iframe').hide();
				var iframe = $('<iframe>', {
					src: '/shell/' + ipaddr,
					'class': 'shell_iframe'
				}).css({height: '100%', width:  '100%'}).attr('data-ip', ipaddr);
				this.$el.find('.instance_shell').append(iframe);
			} else {
				this.$el.find('.shell_iframe').hide();
				currentShell.fadeIn('fast');
			}

			resizeApp();
		}
	},
	add_close_shell: function() {
		this.$el.find('a.instance_shell_tab').append($('<img />', {
			src: site_root+'/resources/images/x_close.png',
			title: 'Terminate Shell',
			'class': 'terminate_shell'
		}));
		this.$el.find('.terminate_shell').attr('data-instance_id', this.model.get('id'));
	},
	terminate_shell: function() {
		var ipaddr = this.model.get('public_dns_name');
		$('.shell_iframe[data-ip="'+ipaddr+'"]').remove();
		$('.instance_tabs a.instance_shell_tab').html("Access by Shell");

		$('.instance_tabs a.instance_info_tab').trigger('click');
		return false;
	}, 
	instance_vnc: function() {
		var ipaddr = this.model.get("public_dns_name");

		if (this.$el.find('.instance_tabs a.instance_vnc_tab').hasClass("tab_disabled")) {
			return false;
		} else {
			var currentVNC = this.$el.find('.vnc_iframe[data-ip="'+ipaddr+'"]');

			if (currentVNC.length == 0) {
				//console.log("Detected that vnc iframe for " + ipaddr + " doesn't exist yet.");	
				var iframe = $('<iframe>', {
					src: 'http://' + ipaddr + ':5904',
					'class': 'vnc_iframe'
				}).css({height: '100%', width:  '100%'}).attr('data-ip', ipaddr);
				this.$el.find('.instance_vnc').append(iframe);
			} else {
				this.$el.find('.vnc_iframe').hide();
				currentVNC.fadeIn('fast');
			}

			resizeApp();
		}

	},
	add_close_vnc: function() {
		this.$el.find('a.instance_vnc_tab').append($('<img/>', {
			src: site_root+'/resources/images/x_close.png',
			title: 'Terminate VNC',
			'class': 'terminate_vnc',
		}));
		this.$el.find('.terminate_vnc').attr('data-instance_id', this.model.get('id'));

	},
	terminate_vnc: function() {
		var ipaddr = this.model.get('public_dns_name');
		$('.vnc_iframe[data-ip="'+ipaddr+'"]').remove();
		$('.instance_tabs a.instance_vnc').html("VNC");

		$('.instance_tabs a.instance_info_tab').trigger('click');
		return false;
	},
	toggle_vis_input: function(e) {
		// Add or remove input box for list of users to access image
		if ($('select[name="vis"] :selected').val() == "select") {
			$('#vis_help').append($('<input/>', {
				name: 'shared_with',
				style: 'display: block',
				type: 'text',
				id: 'shared_with',
				placeholder: 'List their iPlant usernames',
				'class': 'span5'
			}));
		} else {
			if ($('#vis_help').children().length == 1) 
				$($('#vis_help').children()[0]).remove();
		}
	},

	report_instance: function() {

		if (this.$el.find('.report_instance_form').length == 0) {
			new Atmo.Views.ReportInstanceForm({model: this.model}).render().$el.appendTo(this.$el.find('.report_instance'));
		}

		this.$el.find('a.report_instance_tab').fadeIn('fast').trigger('click');
		this.$el.find('.report_instance_form').fadeIn('fast');

	},
	resize_instance: function() {

		if (this.$el.find('.resize_instance_form').length == 0) {
			new Atmo.Views.ResizeInstanceForm({model: this.model}).render().$el.appendTo(this.$el.find('.resize_instance'));
		}

		this.$el.find('a.resize_instance_tab').fadeIn('fast').trigger('click');
		this.$el.find('.resize_instance_form').fadeIn('fast');
	},

	request_imaging: function() {

		if (this.$el.find('.imaging').length == 0) {
			new Atmo.Views.RequestImagingForm({model: this.model}).render().$el.appendTo(this.$el.find('.request_imaging'));
		}

		console.log(this.$el.find('a.request_imaging_tab'));
		console.log(this.$el.find('.imaging_form'));

		this.$el.find('a.request_imaging_tab').fadeIn('fast').trigger('click');
		this.$el.find('.imaging_form').fadeIn('fast');
	},
	edit_instance_info: function(e) {

		var self = this;
		// Remove original 'edit button' and grab original text
		var edit_button = $(e.target).closest('.editable').children();
		var content = edit_button.parent();
		edit_button.remove();
		var text_content = content.text().trim();
		content.removeClass("editable");
		content.unbind('mouseout');
		content.unbind('mouseover');

		// Replace original text with an editable span
		content.html($('<input/>', {
			value: text_content,
			style: 'border: 0px; border-bottom: 1px dotted #999;'
		}));
		content.children().eq(0).focus();

		// Data for Steve to use in each buttons' click functions
		var instance_id = this.model.get('id');
		var type = content.attr('data-type');			// instance_name or instance_tags

		// Append Save Button
		content.append($('<div/>', {
			html: 'Save',
			style: 'display: inline',
			title: 'Save Changes',
			'class': 'save_edit_button',
			click: function() {
				var new_text = content.children().eq(0).val().trim();
				var post_data = {};

				if (new_text.length == 0) {
					
					var header = "Input cannot be empty";
					var body = "You must name your instance.";
					Atmo.Utils.notify(header, body);

					content.children().remove();
					content.html(text_content);
					content.addClass("editable");
					return;
				}
                else if (new_text.length > 127) {
                    var header = "Instance name is too long";
                    var body = "Your instance's name must be less than 128 letters in length.";
                    Atmo.Utils.notify(header, body);
                    return;
                }
				else {
					if (type == 'instance_name') {
						// Change backbone model
						self.model.set({ 
							name: new_text, 
							name_or_id: new_text
						});

						post_data['name'] = new_text;

					}
					else if (type == 'instance_tags') {
						// Change backbone model
						self.model.set({ tags: new_text });

						post_data['tags'] = new_text;

					}

					var id = Atmo.profile.get('selected_identity');

					$.ajax({
						url: '/api/provider/' + id.provider_id + '/identity/' + id.id + '/instance/' + instance_id + '/',
						type: 'PUT',
						data: post_data,
						success: function() {
								$('#refresh_instances_button').click();
						}
					});
				}
				content.children().remove();
				content.html(new_text);
				content.addClass("editable");
                content.append($('<span/>', {
                    class: 'editing', 
                    html: 'Edit Name'
                }));
			}
		}));
	},
	redir_edit_instance_info: function(e) {
		// This function exists to forward event data to the this.edit_instance_info() when a user cicks an editable field instead of using the edit button
		var target =  $(e.target).closest('.editable');
		if (target.children().length == 1)
			this.edit_instance_info(e);
	},
	suspend_resume_instance: function(e) {
		var header = '';		// Title of confirmation modal
		var body = '';			// Body of confirmation modal
		var ok_button = '';		// The text of the confirmation button
		var on_confirm;			// Function to perform if user confirms modal
		var data = {};			// Post data for the action to perform on the instance

		// If the instance is already resuming inform user and return false
		if (this.model.get('state') == 'suspended - resuming') {
			Atmo.Utils.notify('Resuming Instance','Please wait while your instance resumes. Refresh "My Instances" to check its status.');
			return;
		}
		else if (this.model.get('state') == 'active - suspending') {
			Atmo.Utils.notify('Suspending Instance','Please wait while your instance suspend. Refresh "My Instances" to check its status.');
			return;
		}


		var id = Atmo.profile.get('selected_identity');

		var self = this;

		if (this.model.get('state') == 'suspended') {
			header = 'Resume Instance';
			body = 'Your instance\'s IP address may change once it resumes.';
			ok_button = 'Resume Instance';
			data = { "action" : "resume" };
			on_confirm = function() {
				$.ajax({
					url: site_root + '/api/provider/' + id.get('provider_id') + '/identity/' + id.get('id') + '/instance/' + self.model.get('id') + '/action/',
					type: 'POST',
					data: data,
					success: function() {
						Atmo.Utils.notify('Resuming Instance', 'Instance will be active and available shortly.');

						// Merges models to those that are accurate based on server response
						Atmo.instances.update();
					},
					error: function() {
						Atmo.Utils.notify(
							'Could not suspend instance', 
							'If the problem persists, please contact <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', 
							{ no_timeout: true }
						);
					}
				});
			};
		}
		else {
			header = 'Suspend Instance';
			body = '<p class="alert alert-error"><i class="icon-warning-sign"></i> <strong>WARNING</strong> '
				+ 'Suspending an instance will freeze its state, and the IP address may change when you resume the instance.</p>'
				+ 'Suspending an instance frees up resources for other users and allows you to safely preserve the state of your instance without imaging.';
			ok_button = 'Suspend Instance';
			data = { "action" : "suspend" };
			on_confirm = function() {
				$.ajax({
					url: site_root + '/api/provider/' + id.get('provider_id') + '/identity/' + id.get('id') + '/instance/' + self.model.get('id') + '/action/',
					type: 'POST',
					data: data,
					success: function() {
						Atmo.Utils.notify('Suspending Instance', 'Instance will be suspended momentarily.');

						// Merges models to those that are accurate based on server response
						Atmo.instances.update();
					}, 
					error: function() {
						Atmo.Utils.notify(
							'Could not resume instance', 
							'If the problem persists, please contact <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', 
							{ no_timeout: true }
						);
					}
				});
			};
		}

		Atmo.Utils.confirm(header, body, { ok_button: ok_button, on_confirm: on_confirm });
	}
});
