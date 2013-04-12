Atmo.Models.Size = Atmo.Models.Base.extend({
	defaults: { 'model_name': 'size' },
	parse: function(response) {
		var attributes = response;
		
		attributes.id = response.alias;
		attributes.name = response.name;
		attributes.cpus = response.cpu;
		attributes.mem = response.mem;
		attributes.occupancy = response.occupancy;
		attributes.remaining = response.remaining;
		attributes.total = response.total;
		
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

_.extend(Atmo.Models.Size.defaults, Atmo.Models.Base.defaults);

