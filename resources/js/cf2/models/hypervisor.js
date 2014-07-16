Atmo.Models.Hypervisor = Atmo.Models.Base.extend({
	defaults: { 'model_name': 'hypervisor' },
	parse: function(response) {
		var attributes = response;
		
		attributes.id = response.id;
		attributes.name = response.hypervisor_hostname;
		//attributes.cpus = response.cpu;
		//attributes.mem = response.mem;
		//attributes.occupancy = response.occupancy;
		//attributes.remaining = response.remaining;
		//attributes.total = response.total;
		
		return attributes;
	},
	select: function() {
		if (this.collection.selected_instance_type) {
			this.collection.selected_instance_type.set({ selected: false });
		}
		this.collection.selected_instance_type = this;
		this.collection.selected_instance_type.set({ selected: true });
	}
});

_.extend(Atmo.Models.Hypervisor.defaults, Atmo.Models.Base.defaults);

