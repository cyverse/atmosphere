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
		'click .console_instance_btn' : 'console_instance',
		'click .reboot_instance_btn' : 'reboot_instance',
        'click .hard_reboot_instance_btn' : 'hard_reboot_instance',
		'change select[name="vis"]': 'toggle_vis_input',
		'click .editing': 'edit_instance_info',
		'click .editable' : 'redir_edit_instance_info',
        'click a.instance_info_tab' : 'redraw_instance_graph',
		'click .btn.suspend_resume_instance_btn' : 'suspend_resume_instance',
		'click .btn.start_stop_instance_btn' : 'start_stop_instance'
	},
	initialize: function(options) {
		this.model.bind('change:running_shell', this.open_or_close_frames, this);
		this.model.bind('change:running_vnc', this.open_or_close_frames, this);
		this.model.bind('change:state', this.instance_info, this);
		this.model.bind('change:ip_address', this.instance_info, this);
		this.model.bind('change:launch_relative', this.instance_info, this);
        this.model.bind('change:has_shell', this.update_shell_tab, this);
		this.model.bind('change:has_vnc', this.update_vnc_tab, this);
		Atmo.instances.bind('select', this.select_instance, this);
        this.rendered = false;
	},
	update_vnc_tab: function() {
		// If VNC is available, make the tab enabled. Otherwise, disable it.

		var self = this;

		// same for vnc
		if (this.model.get('state_is_active') && this.model.get('has_vnc') == true) {
			this.$el.find('.instance_tabs a.instance_vnc_tab')
				.show()
				.removeClass("disabled")
				.attr("title", "");

			// Get rid of tooltip and 'VNC Unavailable' text
			this.$el.find('.instance_tabs a.instance_vnc_tab').html("Access by VNC");
			this.$el.find('.instance_tabs a.instance_vnc_tab i').remove();
		} 
		else if (this.model.get('has_vnc') == false || this.model.get('has_vnc') == undefined) { 
			this.$el.find('.instance_tabs a.instance_vnc_tab')
				.addClass("disabled")
				.attr("title", "This instance does not support VNC");
			
			// Give you user reasons it might be disabled
			this.$el.find('.instance_tabs a.instance_vnc_tab').html('VNC Unavailable');

			var vnc_help = $('<a/>', {
				class: 'context-helper',
				id: 'help_no_vnc_'+self.model.get('id'),
				html: '<i class="glyphicon glyphicon-question-sign"></i>'
			}).popover({
				title: 'VNC Unavailable <a class="close" data-dismiss="popover" href="#instances" data-parent="help_no_vnc_'+self.model.get('id')+'">&times</a>',
				html: true,
				content: function() {
					var content = 'VNC may be unavailable for several reasons: <ul>'
						+ '<li> Instance is pending, shutting down, or terminated.</li>'
						+ '<li> Instance does not support VNC because it does not have a desktop interface. You can still access it by shell, however.</li>'
						+ '<li> Instance was corrupted during launch. This happens from time to time. Try terminating the instance and launching a new one.</li>'
						+ '</ul>'
						+ 'To guarantee VNC access, launch from an image tagged with "VNC". Do this by searching for <em>tag:vnc</em>.';
					return content;
				},
				placement: 'bottom'
			}).click(this.x_close);

			this.$el.find('.instance_tabs a.instance_vnc_tab').append(vnc_help);
		}

	},
    update_shell_tab: function() {
        var self = this;

		// if shell is available, show it. Otherwise, disable it
		if (this.model.get('state_is_active') && this.model.get('has_shell') == true) {
			this.$el.find('.instance_tabs a.instance_shell_tab')
				.show()
				.removeClass("disabled")
				.attr("title", "");
			
			// Get rid of tooltip and 'Shell Unavailable' text
			this.$el.find('.instance_tabs a.instance_shell_tab').html("Access by Shell");
			this.$el.find('.instance_tabs a.instance_shell_tab i').remove();
		} 
		else if (this.model.get('has_shell') == false || this.model.get('has_shell') == undefined) {
			this.$el.find('.instance_tabs a.instance_shell_tab')
				.addClass("disabled")
				.attr("title", "This instance does not support shell.");

			// Give you user reasons it might be disabled
			this.$el.find('.instance_tabs a.instance_shell_tab').html('Shell Unavailable');

			var shell_help = $('<a/>', {
				class: 'context-helper',
				id: 'help_no_shell_'+self.model.get('id'),
				html: '<i class="glyphicon glyphicon-question-sign"></i>'
			}).popover({
				title: 'Shell Unavailable <a class="close" data-dismiss="popover" href="#instances" data-parent="help_no_shell_'+self.model.get('id')+'">&times</a>',
				html: true,
				content: function() {
					var content = 'The web-based shell may be unavailable for several reasons: <ul>'
						+ '<li> Instance is pending, shutting down, or terminated.</li>'
						+ '<li> Instance is based on an old image and does not support web shell. '
						+ 'Try launching a newer version or connect using Terminal or PuTTY. '
						+ '(<a href="https://pods.iplantcollaborative.org/wiki/x/Oqxm#LoggingIntoanInstance-LoggingintoaninstancewithSSH" target="_blank">Learn How</a>)</li> '
						+ '<li> Instance was corrupted during launch. This happens from time to time. Try terminating the instance and launching a new one.</li>'
						+ '</ul>';
					return content;
				},
				placement: 'bottom'
			}).click(this.x_close);

			this.$el.find('.instance_tabs a.instance_shell_tab').append(shell_help);
		}

    },
	render: function() {
		this.$el.html(this.template(this.model.toJSON()));

		this.$el.data('instance', this.model);
		this.$el.attr('data-instanceid', this.model.get('id'));
		var self = this;
		this.$el.find('.instance_tabs a.instance_shell_tab, .instance_tabs a.instance_vnc_tab').addClass("disabled");

		// Enable Shell/VNC if instance has those available
        this.update_shell_tab();
        this.update_vnc_tab();

		// Display 'Request Imaging' tab if they've already clicked the button for this instance before	
		if (this.$el.find('.module[data-ip="'+this.model.get('public_dns_name')+'"]').length != 0)
			this.$el.find('a.request_imaging').fadeIn('fast');
		else
			this.$el.find('a.request_imaging').fadeOut('fast');

		this.display_close_buttons();

		// If instance is resizing, display resize tab and automatically navigate to it
		if (this.model.get('state').indexOf('resize') != -1)
			this.resize_instance();

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
		    this.instance_graph = new Atmo.Views.InstanceGraphContainer({model: this.model, el: this.$el.find('.instance_graph')}).render();
        }
    },
	instance_info: function() {
		this.$el.find('.instance_info').html(_.template(Atmo.Templates.instance_info_tab, this.model.toJSON()));

		var self = this;
        var ip_span = this.$el.find('#instance-ip-span');
        if (this.model.get('public_dns_name') == "0.0.0.0") {
            //Clear the IP address field
            ip_span.html("");
        }
		// Display OpenStack-specific options
		if (Atmo.profile.get('selected_identity').get('provider').match(/openstack/i) || Atmo.profile.get('selected_identity').get('provider').match(/iplant/i) ) {

			// Display descriptive instance size
			var types = _.filter(Atmo.instance_types.models, function(type) {
				return type.get('alias') == self.model.get('size_alias');
			});
			var instance_type = types[0];
            var digits = (instance_type.get('mem') % 1024 == 0) ? 0 : 1;
            if (instance_type.get('disk') != 0) {
                var disk_str = ', ' + instance_type.get('disk') + ' GB disk';
            }  else {
                var disk_str = '';
            }
            if (instance_type.get('root') != 0) {
                var root_str = ', ' + instance_type.get('root') + ' GB root';
            }  else {
                var root_str = '';
            }
            var cpu_str = instance_type.get('cpus') + ' CPUs';
            // Make a human readable number
            var mem = (instance_type.get('mem') > 1024) ? '' + (instance_type.get('mem') / 1024).toFixed(digits) + ' GB' : (instance_type.get('mem') + ' MB') ;
            var mem_str = mem + ' memory';
            var instance_str = instance_type.get('name') + ' (' + cpu_str + ', ' + mem_str + disk_str + root_str + ')';
			self.$el.find('.instance_size').html(instance_str);

			this.$el.find('#euca_controls').remove();

			// Disable if instance is not running
			if (!this.model.get('state_is_active')) {
                            var state = this.model.get('state');
			    if (state != 'active' && (state == 'suspended - resuming' || state == 'active - suspending')) {
				    this.$el.find('.reboot_instance_btn').addClass('disabled').attr('disabled', 'disabled');
				    this.$el.find('.hard_reboot_instance_dropdown').addClass('disabled').attr('disabled', 'disabled');
				    this.$el.find('.hard_reboot_instance_btn').addClass('disabled').attr('disabled', 'disabled');
				    this.$el.find('.suspend_resume_instance_btn').addClass('disabled').attr('disabled', 'disabled');
				}
				this.$el.find('.request_imaging_btn').addClass('disabled').attr('disabled', 'disabled');
				this.$el.find('.report_instance_btn').addClass('disabled').attr('disabled', 'disabled');
				this.$el.find('.start_stop_instance_btn').addClass('disabled').attr('disabled', 'disabled');
				this.$el.find('a[href^="#request_imaging"]').hide();

				if (this.model.get('state').indexOf('resize') == -1) {
					this.$el.find('.resize_instance_btn').addClass('disabled').attr('disabled', 'disabled');
					this.$el.find('a[href^="#resize_instance"]').hide();
				}
				else {
					this.$el.find('.resize_instance_btn').removeClass('disabled').removeAttr('disabled', 'disabled');
					this.$el.find('a[href^="#resize_instance"]').show();
				}
			}

			// Don't permit terminate if instance is suspended
			//if (this.model.get('state_is_inactive'))
			//	this.$el.find('.terminate_instance').addClass('disabled').attr('disabled', 'disabled');

			// Show appropriate controls
			this.$el.find('#openstack_controls').fadeIn('fast');

			if (this.model.get('state') == 'suspended') {
				var resume_button = this.$el.find('.btn.suspend_resume_instance_btn');
                resume_button.html('<i class="glyphicon glyphicon-play"></i> Resume');
                resume_button.removeClass('disabled').removeAttr('disabled');
            } else {
				this.$el.find('.btn.suspend_resume_instance_btn').fadeIn('fast');
            }
			if (this.model.get('state') == 'shutoff') {
				var start_button = this.$el.find('.btn.start_stop_instance_btn');
                start_button.html('<i class="glyphicon glyphicon-share-alt"></i> Start');
                start_button.removeClass('disabled').removeAttr('disabled');
            } else {
				this.$el.find('.btn.start_stop_instance_btn').fadeIn('fast');
		    }
		}
		else {
			this.$el.find('#openstack_controls').remove();

			// Disable if instance is not running
			if (!this.model.get('state_is_active')) {
				this.$el.find('.request_imaging_btn').addClass('disabled').attr('disabled', 'disabled');
				this.$el.find('.report_instance_btn').addClass('disabled').attr('disabled', 'disabled');
				this.$el.find('.reboot_instance_btn').addClass('disabled').attr('disabled', 'disabled');
				this.$el.find('.hard_reboot_instance_dropdown').addClass('disabled').attr('disabled', 'disabled');
				this.$el.find('.hard_reboot_instance_btn').addClass('disabled').attr('disabled', 'disabled');
				this.$el.find('#instance_tabs a[href="#instance_shell"]').addClass("disabled");
				this.$el.find('#instance_tabs a[href="#instance_vnc"]').addClass("disabled");
			}

			// Don't permit terminate if instance is suspended
			if (this.model.get('state_is_inactive'))
				this.$el.find('.terminate_instance').addClass('disabled').attr('disabled', 'disabled');

			this.$el.find('#euca_controls').fadeIn('fast');
		}
        this.display_graph();

		// Shutting-down/terminted instances should have terminate button disabled
		if (this.model.get('state_is_delete')) {
			this.$el.find('.terminate_instance').addClass('disabled').attr('disabled', 'disabled');
			this.$el.find('.suspend_resume_instance_btn').addClass('disabled').attr('disabled', 'disabled');
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
		
		if (this.$el.find('.instance_tabs a[href="#instance_shell"]').hasClass("disabled")) {
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

		if (this.$el.find('.instance_tabs a.instance_vnc_tab').hasClass("disabled")) {
			return false;
		} else {
			var currentVNC = this.$el.find('.vnc_iframe[data-ip="'+ipaddr+'"]');

			if (currentVNC.length == 0) {
                var iframe = $('<a>', {href: 'http://' + ipaddr + ':5904'})
                    .addClass('vnc_iframe')
                    .attr('target', '_blank')
                    .append("Launch VNC")
                    .attr('data-ip', ipaddr);
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
	console_instance: function() {
		Atmo.Utils.notify('Launching Instance Console', 'The new console window will appear in a new tab momentarily.');
        data = {"action":"console"};
	    var newtab = window.open(url, '_blank');
		var ident = Atmo.profile.get('selected_identity');
		var instance_id = this.model.get('id');
		$.ajax({
			url: site_root + '/api/v1/provider/' + ident.get('provider_id') + '/identity/' + ident.get('id') + '/instance/' + instance_id + '/action/',
			type: 'POST',
			data: data,
			success: function(result_obj) {
                url = result_obj['object']
                newtab.location = url;
			},
			error: function(request, status, error) {
			   Atmo.Utils.notifyErrors(request, 'Could not stop instance for the following error(s):');	
			}
		});
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
		}).on('keypress', function(e) {
			// Allow user to submit by pressing 'enter'
            if (e.keyCode == 13)
				self.handle_instance_update(content, content.attr('data-type'));
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
				self.handle_instance_update(content, content.attr('data-type'));
			}
		}));
	},
	handle_instance_update: function(content, type) {
		var new_text = content.children().eq(0).val().trim();
		var post_data = {};
		var self = this;

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
				post_data['name'] = new_text;
			}
			else if (type == 'instance_tags') {
				post_data['tags'] = new_text;
			}

			self.model.save(post_data, 
				{ patch: true, 
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
	},
	redir_edit_instance_info: function(e) {
		// This function exists to forward event data to the this.edit_instance_info() when a user cicks an editable field instead of using the edit button
		var target =  $(e.target).closest('.editable');
		if (target.children().length == 1)
			this.edit_instance_info(e);
	},
	reboot_instance: function(e) {
	    var header = '',
            body = '',
            ok_button = '',
            on_confirm,
            data = {},
            identity_id = Atmo.profile.get('selected_identity'),
            identity = Atmo.identities.get(identity_id),
            provider_name = identity.get('provider').get('type'),
            provider_name_lowercase = provider_name.toLowerCase(),
            self = this;

		header = 'Reboot Instance';

		// Reboot is hard or soft depending on whether you're on OpenStack or Eucalyptus, respectively
		if (provider_name_lowercase === 'openstack') {
			body = '<p class="alert alert-error"><i class="glyphicon glyphicon-question-sign"></i> <strong>WARNING</strong> '
				+ 'Rebooting an instance will cause it to temporarily shut down and become inaccessible during that time.';
		}
		else {
			body = 'Your instance will perform a soft reboot.';
		}

		ok_button = 'Reboot Instance';
		data = { "action" : "reboot" };
		on_confirm = function() {
			Atmo.Utils.notify('Instance is rebooting...', 'Instance will finish rebooting momentarily.');
			$.ajax({
				url: site_root + '/api/v1/provider/' +
                     identity_id.get('provider_id') + '/identity/' + identity_id.get('id') 
                     + '/instance/' + self.model.get('id') + '/action/',

				type: 'POST',
				data: data,
				success: function() {
					// Merges models to those that are accurate based on server response
					Atmo.instances.update();
					if (provider_name_lowercase !== 'openstack')
						Atmo.Utils.notify("Reboot Successful", "Your instance has successfully performed a soft reboot.");
				}, 
				error: function(request,model,error) {
				  Atmo.Utils.notifyErrors(request,'Could not reboot instance for the following reason(s):');					
				}
			});
		};

		Atmo.Utils.confirm(header, body, { ok_button: ok_button, on_confirm: on_confirm });
	},

    hard_reboot_instance: function(e){
        var header = '',
            body = '',
            ok_button = '',
            on_confirm,
            data = {},
            identity_id = Atmo.profile.get('selected_identity'),
            identity = Atmo.identities.get(identity_id),
            provider_name = identity.get('provider').get('type'),
            provider_name_lowercase = provider_name.toLowerCase(),
            self = this;

        header = 'Hard Reboot Instance';

        if(provider_name_lowercase === 'openstack'){
            body = '<p class="alert alert-error"><i class="glyphicon glyphicon-question-sign"></i> <strong>WARNING</strong> '
                 + 'Rebooting an instance will cause it to temporarily shut down and become inaccessible during that time.';
        }
        else{
            body = 'Your instance will perform a soft reboot.';
        }

        ok_button = 'Hard Reboot Instance';
        data = { action : "reboot" , reboot_type : "HARD" };
        on_confirm = function(){
            Atmo.Utils.notify('Instance is hard rebooting...', 'Instance will finish rebooting momentarily.');
            $.ajax({
                url: site_root + '/api/v1/provider/' +
                     identity_id.get('provider_id') + '/identity/' +
                     identity_id.get('id') + '/instance/' +
                     self.model.get('id') + '/action/',

                type: 'POST',
                data: data,
                success: function(){
                    Atmo.instances.update();
                    if(provider_name_lowercase !== 'openstack')
                        Atmo.Utils.notify("Reboot Successful", "Your instance has successfully performed a soft reboot.");
                },
                error: function(request, model, error){
                    Atmo.Utils.notifyErrors(request,'Could not reboot instance for the following reason(s):');
                }
            });
        };

        Atmo.Utils.confirm(header, body, { ok_button: ok_button, on_confirm: on_confirm });
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

			// Make sure user has enough quota to resume this instance
			if (this.check_quota()) {
				ok_button = 'Resume Instance';
				data = { "action" : "resume" };
				body = 'Your instance\'s IP address may change once it resumes.';
				on_confirm = function() {

					// Prevent user from being able to quickly resume multiple instances and go over quota
					self.model.set({state: 'suspended - resuming',
									state_is_build: true,
									state_is_inactive: false});

					Atmo.Utils.notify('Resuming Instance', 'Instance will be active and available shortly.');
					$.ajax({
						url: site_root + '/api/v1/provider/' + id.get('provider_id') + '/identity/' + id.get('id') + '/instance/' + self.model.get('id') + '/action/',
						type: 'POST',
						data: data,
						success: function() {
							Atmo.instances.update();
						},
						error: function(request, status, error) {
						   self.model.set({state: 'suspended',
											state_is_build: false,
											state_is_inactive: true});

						  Atmo.Utils.notifyErrors(request,'You could not resume your instance for the following reason(s):');
						}
					});
				};
			}
			else {
				body = '<p class="alert alert-error"><i class="glyphicon glyphicon-ban-circle"></i> <strong>Cannot resume instance</strong> '
					+ 'You do not have enough resources to resume this instance. You must terminate, suspend, or stop another running instance, or request more resources.';
				ok_button = 'Ok';
			}
		}
		else {
			header = 'Suspend Instance';
			body = '<p class="alert alert-error"><i class="glyphicon glyphicon-warning-sign"></i> <strong>WARNING</strong> '
				+ 'Suspending an instance will freeze its state, and the IP address may change when you resume the instance.</p>'
				+ 'Suspending an instance frees up resources for other users and allows you to safely preserve the state of your instance without imaging. '
				+ 'Your time allocation no longer counts against you in the suspended mode.'
				+ '<br><br>'
				+ 'Your resource usage charts will only reflect the freed resources once the instance\'s state is "suspended."';
			ok_button = 'Suspend Instance';
			data = { "action" : "suspend" };
			on_confirm = function() {
				Atmo.Utils.notify('Suspending Instance', 'Instance will be suspended momentarily.');

				$.ajax({
					url: site_root + '/api/v1/provider/' + id.get('provider_id') + '/identity/' + id.get('id') + '/instance/' + self.model.get('id') + '/action/',
					type: 'POST',
					data: data,
					success: function() {
						// Merges models to those that are accurate based on server response
						Atmo.instances.update();
					}, 
					error: function(request,status,error) {
					  self.model.set({ state_is_active: true, state_is_build: false });
					  Atmo.Utils.notifyErrors(request, 'You could not suspend your instance for the following reason(s):');
					}
				});
			};
		}

		Atmo.Utils.confirm(header, body, { ok_button: ok_button, on_confirm: on_confirm });
	},
	start_stop_instance: function(e) {
		var header = '';		// Title of confirmation modal
		var body = '';			// Body of confirmation modal
		var ok_button = '';		// The text of the confirmation button
		var on_confirm;			// Function to perform if user confirms modal
		var data = {};			// Post data for the action to perform on the instance

		// If the instance is already starting/stopping inform user and return false
		if (this.model.get('state') == 'active - powering-off') {
			Atmo.Utils.notify('Stopping Instance','Please wait while your instance stops. Refresh "My Instances" to check its status.');
			return;
		}
		else if (this.model.get('state') == 'shutoff - powering-on') {
			Atmo.Utils.notify('Starting Instance','Please wait while your instance starts. Refresh "My Instances" to check its status.');
			return;
		}

		var id = Atmo.profile.get('selected_identity');
		var self = this;

		if (this.model.get('state') == 'shutoff') {
			// Make sure user has enough quota to resume this instance
			if (this.check_quota()) {
				header = 'Start Instance';
				body = '<p class="alert alert-error"><i class="glyphicon glyphicon-warning-sign"></i> <strong>WARNING</strong> '
					+ 'In order to start a stopped instance, you must have sufficient quota and the cloud must have enough room to support your instance\'s size.';
				ok_button = 'Start Instance';
				data = { "action" : "start" };
				on_confirm = function() {
					Atmo.Utils.notify('Starting Instance', 'Instance will be available momentarily.');

					// Prevent user from being able to quickly start multiple instances and go over quota
					self.model.set({state: 'shutoff - powering-on',
									state_is_build: true,
									state_is_inactive: false});

					$.ajax({
						url: site_root + '/api/v1/provider/' + id.get('provider_id') + '/identity/' + id.get('id') + '/instance/' + self.model.get('id') + '/action/',
						type: 'POST',
						data: data,
						success: function() {
							// Merges models to those that are accurate based on server response
							Atmo.instances.update();
						}, 
						error: function(request, status, error) {
							self.model.set({state: 'shutoff',
											state_is_build: false,
											state_is_inactive: true});
							Atmo.Utils.notifyErrors(request,'Coult not start instance for the following reason(s):');
						}
					});
				};
			}
			else {
				body = '<p class="alert alert-error"><i class="glyphicon glyphicon-ban-circle"></i> <strong>Cannot start instance</strong> '
					+ 'You do not have enough resources to start this instance. You must terminate, suspend, or stop another running instance, or request more resources.';
				ok_button = 'Ok';
			}
		}
		else {
			header = 'Stop Instance';
			body = 'Your instance will be stopped.<br /><br/><strong>NOTE:</strong> This will NOT affect your resources. To preserve resources and time allocation you must Suspend your instance.';
			ok_button = 'Stop Instance';
			data = { "action" : "stop" };
			on_confirm = function() {
				Atmo.Utils.notify('Stopping Instance', 'Instance will be stopped momentarily.');
				$.ajax({
					url: site_root + '/api/v1/provider/' + id.get('provider_id') + '/identity/' + id.get('id') + '/instance/' + self.model.get('id') + '/action/',
					type: 'POST',
					data: data,
					success: function() {
						//Atmo.Utils.notify('Resuming Instance', 'Instance will be active and available shortly.');
						// Merges models to those that are accurate based on server response
						Atmo.instances.update();
					},
					error: function(request, status, error) {
					   Atmo.Utils.notifyErrors(request, 'Could not stop instance for the following error(s):');	
					}
				});
			};
		}

		Atmo.Utils.confirm(header, body, { ok_button: ok_button, on_confirm: on_confirm });
	},
	check_quota: function() {

		// Before we allow a user to suspend/resume, we need to be sure they have enough quota
		var used_mem = 0;
		var used_cpu = 0;
		var quota_mem = Atmo.profile.get('selected_identity').get('quota').mem;
		var quota_cpu = Atmo.profile.get('selected_identity').get('quota').cpu;
		var instances_to_add = Atmo.instances.get_active_instances();
		instances_to_add.push(this.model);

		if (Atmo.instance_types.models.length > 0) {

			for (var i = 0; i < instances_to_add.length; i++) {
				var instance = instances_to_add[i];

				var instance_type = instance.get('type');
				var to_add = _.filter(Atmo.instance_types.models, function(model) {
					return model.attributes.alias == instance_type;
				});
				used_mem += to_add[0]['attributes']['mem'];
				used_cpu += to_add[0]['attributes']['cpu'];
			}
		}

		return used_mem <= quota_mem && used_cpu <= quota_cpu;

	}
});
