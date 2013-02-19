/* Volume views */
Atmo.Views.VolumeScreen = Backbone.View.extend({
	tagName: 'div',
	className: 'screen',
	id: 'volumeList',
	template: _.template(Atmo.Templates.volume_screen),
    events: {
        'click #report_broken_volume_btn':'report_volume_modal'
    },
	initialize: function() {
		Atmo.volumes.bind("reset", this.render, this);
		Atmo.instances.bind("reset", this.render, this);
	},
	render: function(e) {
		this.$el.html(this.template());
        var self = this;

        // Create context help for a few volume functions
        this.$el.find('#help_available_volumes').popover({
            placement: 'top',
            html: true,
            title: 'Available Volumes <a class="close" data-parent="help_available_volumes" data-dismiss="popover" href="#volumes">&times</a>',
            content: function() {
                var content = 'A volume is <b>available</b> when it is not attached to an instance. ';
                content += 'Any newly created volume <u>must</u> be <strong>formatted</strong> and then <strong>mounted</strong> after it has been attached before you will be able to use it. (<a href="https://pods.iplantcollaborative.org/wiki/x/OKxm/#AttachinganEBSVolumetoanInstance-Step5%3ACreatethefilesystem%28onetimeonly%29." target="_blank">Learn How</a>)<br /><br />';
                content += 'More information about volumes: <ul>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm" target="_blank">Creating a Volume</a></li>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step3%3AAttachthevolumetotherunninginstance." target="_blank">Attaching a Volume to an Instance</a></li>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step5%3ACreatethefilesystem%28onetimeonly%29." target="_blank">Formatting a Volume</a></li>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step6%3AMountthefilesystemonthepartition." target="_blank">Mounting a Volume</a></li>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step7%3AUnmountanddetachthevolume." target="_blank">Unmounting and Detaching Volume</a></li>';
                content += '</ul>';
                return content;
            }
        }).click(this.x_close);

        // Assign the 'x' button some close functionality -- not default in bootstrap

        this.$el.find('#help_my_volumes').popover({
            placement: 'bottom',
            title: 'My Volumes <a class="close" data-dismiss="popover" href="#volumes" data-parent="help_my_volumes">&times</a>',
            html: true,
            content: function() {
                var content = 'A <strong>volume</strong> is like a virtual USB drive, and makes it easy to transfer relatively small data between instances.<br /><br />';
                content += 'You can create a volume with a capacity up to 100 GB using the "Create a Volume" form. To store and transfer more data at once, store it in the iPlant Data Store instead. You can mount the Data Store similarly to a volume. (<a href="https://pods.iplantcollaborative.org/wiki/x/S6xm" target="_blank">Learn How</a>)<br /><br />';
                content += 'More information about volumes: <ul>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm" target="_blank">Creating a Volume</a></li>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step3%3AAttachthevolumetotherunninginstance." target="_blank">Attaching a Volume to an Instance</a></li>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step5%3ACreatethefilesystem%28onetimeonly%29." target="_blank">Formatting a Volume</a></li>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step6%3AMountthefilesystemonthepartition." target="_blank">Mounting a Volume</a></li>';
                content += '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step7%3AUnmountanddetachthevolume." target="_blank">Unmounting and Detaching Volume</a></li>';
                content += '</ul>';
                return content;
            }
        }).click(this.x_close);


		new Atmo.Views.VolumeScreenControls({el: this.$el.find('#volume_controls')}).render();
		new Atmo.Views.VolumeScreenDraggableInstances({el: this.$el.find('#draggable_instances')}).render();
		new Atmo.Views.VolumeScreenDraggableVolumes({el: this.$el.find('#draggable_volumes')}).render();

		return this;
	},
    x_close: function() {

        // Must assign this function after the popover is actually rendered, so we find '.close' element
        $('.close').click(function(e) {
            e.preventDefault();
            var popover_parent = $(this).data('parent');
            if (popover_parent != undefined) {
                $('#'+popover_parent).popover('hide');
            }            
        });
    },
    report_volume_modal: function() {

        // Create a modal for reporting broken volumes
        var ok_button = '';
        var header = 'Report a Volume';
        var body = '';
        if (Atmo.volumes.models.length > 0) {

            ok_button = 'Report Volume';

            body += '<p class="alert alert-info"><i class="icon-info-sign"></i> First, it may help to read about <a href="https://pods.iplantcollaborative.org/wiki/x/OKxm" target="_blank">using volumes</a> and <a href="https://pods.iplantcollaborative.org/wiki/x/p55y" target="_blank">troubleshooting volumes</a>.</p>';
            body += '<form name="report_volume_form">';
            body += '<h3>Select the volume to report.</h3>';
            body += '<div class="row-fluid"><div class="span11 offset1">';

            body += '<select name="broken_volume">';
                // Loop through all volumes
                for (var i = 0; i < Atmo.volumes.models.length; i++) {
                    body += '<option value="' + Atmo.volumes.models[i].get('id') + '">' + Atmo.volumes.models[i].get('name_or_id');
						// If the volume has a name, show ID in parens
						if (Atmo.volumes.models[i].get('name') != Atmo.volumes.models[i].get('id'))
							body += ' (' + Atmo.volumes.models[i].get('id') + ')';
					body += '</option>';
                }
            body +='</select>';
            body += '</div></div>';
            body += '<h3>What problem(s) are you having with this volume?</h3>';
            body += '<div class="row-fluid"><div class="span11 offset1">';
            body += '<label class="checkbox"><input type="checkbox" value="Cannot attach/detach"> Volume does not successfully attach or detach.</label>';
            body += '<label class="checkbox"><input type="checkbox" value="Cannot mount/unmount"> Volume does not successfully mount or unmount.</label>';
            body += '<label class="checkbox"><input type="checkbox" value="Missing Data"> Data is missing from my volume.</label>';
            body += '<label class="checkbox"><input type="checkbox" value="Cannot transfer data on/off volume"> Cannot transfer data on/off my volume.</label>';
            body += '</div></div>';
            body += '<h3>Please provide as many details about the problem as possible.</h3>';
            body += '<div class="row-fluid"><div class="span11 offset1">';
            body += '<textarea name="problem_details" style="width: 80%" rows="5"></textarea>';
            body += '</div></div>';
        }
        else {
            body += '<p class="alert alert-info"><i class="icon-info-sign"></i> You don\'t have any volumes.</p>'
            body += 'If you need help with something else, please contact the Atmosphere support team. You can: ';
            body += '<ul><li>Email <a href="mailto:atmo@iplantcollaborative.org">atmo@iplantcollaborative.org</a></li>';
            body += '<li>Use the feedback form by clicking the "Tell us what you think!" button in the footer</li></ul>';
            ok_button = 'Ok';
        }

        Atmo.Utils.confirm(header, body, {
            on_confirm: function() {

                if (Atmo.volumes.models.length > 0) {

                    var data = {};
                    data["message"] = '';
                    data["username"] = Atmo.profile.get('id');
                    data["subject"] = 'Atmosphere Volume Report from ' + data["username"];

                    var inputs = $('form[name="report_volume_form"] select, form[name="report_volume_form"] textarea');
                    var selects = $('form[name="report_volume_form"] input[type="checkbox"]');

					// Only fetch values from selected checkboxes
					for (var i = 0; i < selects.length; i++) {
						if ($(selects[i]).is(':checked')) {
							inputs.push(selects[i]);
						}
					}
					
					// Add all inputs to outgoing message
                    for (var i = 0; i < inputs.length; i++) {

                        data["message"] += $(inputs[i]).val() + '\n';

                        if ($(inputs[i]).attr('type') != 'checkbox') {
                           data["message"] += '\n';
                        }

                    }

					data["message"] += '\n\n' + 'Provider ID: ' + Atmo.profile.get('selected_identity').get('provider_id') + '\n';

                    $.ajax({
                        type: 'POST',
                        url: site_root + '/api/email_support/', 
                        data: data,
                        success: function() {
                            Atmo.Utils.notify("Volume Reported", "Support will contact you shortly");
                        },
                        dataType: 'json'
                    });
                }
            }, 
            ok_button: ok_button
        });
    }
});
