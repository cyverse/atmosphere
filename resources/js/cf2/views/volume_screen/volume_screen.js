/** 
 *
 * Creates all the components of the volumes screen as separate views. 
 *
 */
Atmo.Views.VolumeScreen = Backbone.View.extend({
	tagName: 'div',
	className: 'screen',
	id: 'volumeList',
	template: _.template(Atmo.Templates.volume_screen),
    events: {
        'click #report_broken_volume_btn':'report_volume_modal',
        'click #backup_volume_btn':'backup_volume_modal',
		'click #restore_volume_btn':'restore_volume_modal'
    },
	initialize: function() {
		Atmo.volumes.bind("reset", this.render, this);
		Atmo.instances.bind("reset", this.render, this);
	},
	render: function(e) {
		this.$el.html(this.template());
        var self = this;

	  //console.log("Rendering volume screen.");

        // Create context help for a few volume functions
        this.$el.find('#help_available_volumes').popover({
            placement: 'bottom',
            html: true,
            title: 'Available Volumes <a class="close" data-parent="help_available_volumes" data-dismiss="popover" href="#volumes">&times</a>',
            content: function() {
                var content = 'A volume is <b>available</b> when it is not attached to an instance. '
                	+ 'Any newly created volume <u>must</u> be <strong>formatted</strong> and then <strong>mounted</strong> after it has been attached before you will be able to use it. (<a href="https://pods.iplantcollaborative.org/wiki/x/OKxm/#AttachinganEBSVolumetoanInstance-Step5%3ACreatethefilesystem%28onetimeonly%29." target="_blank">Learn How</a>)<br /><br />'
                	+ 'More information about volumes: <ul>'
                	+ '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm" target="_blank">Creating a Volume</a></li>'
                	+ '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step3%3AAttachthevolumetotherunninginstance." target="_blank">Attaching a Volume to an Instance</a></li>'
                	+ '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step5%3ACreatethefilesystem%28onetimeonly%29." target="_blank">Formatting a Volume</a></li>'
                	+ '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step6%3AMountthefilesystemonthepartition." target="_blank">Mounting a Volume</a></li>'
                	+ '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step7%3AUnmountanddetachthevolume." target="_blank">Unmounting and Detaching Volume</a></li>'
                	+'</ul>';

                return content;
            }
        }).click(this.x_close);

        // Assign the 'x' button some close functionality -- not default in bootstrap

        this.$el.find('#help_my_volumes').popover({
            placement: 'bottom',
            title: 'My Volumes <a class="close" data-dismiss="popover" href="#volumes" data-parent="help_my_volumes">&times</a>',
            html: true,
            content: function() {
                var content = 'A <strong>volume</strong> is like a virtual USB drive, and makes it easy to transfer relatively small data between instances.<br /><br />'
                	+ 'You can create a volume up to the capacity allowed by your Storage Quota using the "Create a Volume" form. If you need more data then is allowed by your Storage Quota, store it in the iPlant Data Store instead. You can mount the Data Store similarly to a volume. (<a href="https://pods.iplantcollaborative.org/wiki/x/S6xm" target="_blank">Learn How</a>)<br /><br />'
                	+ 'More information about volumes: <ul>'
                	+ '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm" target="_blank">Creating a Volume</a></li>'
                	+ '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step3%3AAttachthevolumetotherunninginstance." target="_blank">Attaching a Volume to an Instance</a></li>'
                	+ '<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step5%3ACreatethefilesystem%28onetimeonly%29." target="_blank">Formatting a Volume</a></li>'
                	+'<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step6%3AMountthefilesystemonthepartition." target="_blank">Mounting a Volume</a></li>'
                	+'<li><a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step7%3AUnmountanddetachthevolume." target="_blank">Unmounting and Detaching Volume</a></li>'
                	+ '</ul>';

                return content;
            }
        }).click(this.x_close);


		new Atmo.Views.VolumeScreenControls({el: this.$el.find('#volume_controls')}).render();
		new Atmo.Views.VolumeScreenDraggableInstances({el: this.$el.find('#draggable_instances')}).render();
		new Atmo.Views.VolumeScreenDraggableVolumes({el: this.$el.find('#draggable_volumes')}).render();
		this.backup_volume_modal = new Atmo.Views.BackupVolumeModal({el: this.$el.find('#backup_modal')});
		this.backup_volume_modal.render();
		this.restore_volume_modal = new Atmo.Views.RestoreVolumeModal({el: this.$el.find('#restore_modal')});
		this.restore_volume_modal.render();
		this.report_volume_modal = new Atmo.Views.ReportVolumeModal({el: this.$el.find('#report_modal')});
		this.report_volume_modal.render();

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
		this.report_volume_modal.do_alert();
    },
    backup_volume_modal: function() {
		this.backup_volume_modal.do_alert();
    },
    restore_volume_modal: function() {
		this.restore_volume_modal.do_alert();
    }
});
