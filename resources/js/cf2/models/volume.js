Atmo.Models.Volume = Atmo.Models.Base.extend({
	defaults: { 'model_name': 'volume' },
	parse: function(response) {
		
		var attributes = response;
		
		attributes.id = response.alias;
		attributes.name_or_id = response.name.length == 0 ? response.alias : response.name;
		attributes.create_time = new Date(response.start_date);
		attributes.create_relative = Atmo.Utils.relative_time(attributes.create_time);
		
		var attach_data = response.attach_data;
		
		if (!jQuery.isEmptyObject(attach_data)) {
			attributes.attach_data_attach_time = new Date(attach_data.attachTime);
			attributes.attach_data_attach_relative = Atmo.Utils.relative_time(attributes.attach_data_attach_time);
			attach_data.attachRelative = attributes.attach_data_attach_relative;
			attributes.attach_data_device = attach_data.device;
			attributes.attach_data_instance_id = attach_data.instanceId;
		} 
		else {
			attributes.attach_data_attach_time = null;
			attributes.attach_data_device = null
			attributes.attach_data_instance_id = null;
		}
		
		return attributes;
	},
	get_available: function() {
		return _.filter(this.models, function(model) {
			return model.get('status') == 'available';
		});
	},
	attach_to: function(instance, mount_location, options) {
		if (!options) options = {};
		if (!options.success) options.success = function() {};

		if (!options.error) options.error = function() {
			var header = "Something broke!";
			var body = 'You can refresh the page and try to perform this operation again. If the problem persists, please email '
				+ '<a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>. <br /><br />We apologize for the inconvenience.';
			Atmo.Utils.notify(header, body);
		}
		
		this.set({
			'status': 'attaching',
			'attach_data_instance_id': instance.get('id')
		});
		
		var param = {
			volume_id: this.get('id'),
			action: "attach_volume",
			mount_location: mount_location
		};
  
		var self = this;
		var action_url = instance.url() + 'action/';

		$.ajax({
			url: action_url, 
			type : 'POST', 
			data: param, 
			success:function(response_text, textStatus, jqXHR) {
				self.set({
					'attach_data_attach_time': null,
					'attach_data_device': response_text.object.attach_data.device, 
					'attach_data_instance_id': instance.get('id'),
					'status': 'in-use'
				});
				
				self.trigger('attach');
				options.success(response_text);
			}, 
			error: function (jqXHR, textStatus, errorThrown) {
				self.set({
					'status': 'available',
					'attach_data_instance_id': null
				});
				
				options.error('failed to attach volume');
			}
		});
	},
	detach: function(instance, options) {
		if (!options) options = {};
		if (!options.success) options.success = function() {};
		if (!options.error) options.error = function() {
			var header = "Something broke!";
			var body = "You can refresh the page and try to perform this operation again. If the problem persists, please email " +
				'<a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>. <br /><br />We apologize for the inconvenience.';
			Atmo.Utils.notify(header, body);
		};
	
		var param = {
			volume_id: this.get('id'),
			action: "detach_volume"
		};
		
		this.set({'status': 'detaching'});
		var self = this;
		var action_url = instance.url() + 'action/';
		
		$.ajax({
			url: action_url, 
			type: "POST", 
			data: param, 
			success: function(response_data) {
				self.set({
					//'attach_data_attach_time': null,
					//'attach_data_device': null,
					//'attach_data_instance_id': null,
					'status': 'detaching'
				});
				self.trigger('detach');
				options.success();
			},
			error: function(response_data) {
				options.error('failed to detach volume', response_data);
				self.set({'status': 'in-use'});
			}
		});
	},
	confirm_destroy: function(options) {
		if (!options) options = {};
		if (!options.error) options.error = function() {
			var header = "Something broke!";
			var body = 'You can refresh the page and try to perform this operation again. If the problem persists, please email '
				+ '<a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>. <br /><br />We apologize for the inconvenience.';
			Atmo.Utils.notify(header, body);
		};

		var volname = this.get('name_or_id');
		var self = this;
		var header = "Do you want to destroy this volume?";
		var body = "Your volume <strong>" + volname + "</strong> will be destroyed and all data will be permanently lost!";
		
		Atmo.Utils.confirm(header, body, { 
			on_confirm: function() {
				self.destroy({
					wait: true,
					success: options.success,
					error: options.error
				});
			},
			ok_button: 'Yes, destroy this volume'
		}); 
	}
});

_.extend(Atmo.Models.Volume.defaults, Atmo.Models.Base.defaults);
