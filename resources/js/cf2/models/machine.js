Atmo.Models.Machine = Atmo.Models.Base.extend({
	defaults: { 'model_name': 'machine' },
	initialize: function () {
		this.set('name_or_id', this.get('name') || this.get('id'));
	},
	parse: function(response) {
		var attributes = response;
		
		attributes.id = response.alias;
		attributes.name = response.name;
		attributes.architecture = response.architecture;
		attributes.create_date = response.start_date;
		attributes.featured = response.featured;

		if (response.icon)
			attributes.image_url = response.icon;
		else
			attributes.image_url = Atmo.profile.get_icon(response.alias_hash);

		attributes.ownerid = response.ownerid;
		attributes.state = response.state;
		
		return attributes;
	}
});

_.extend(Atmo.Models.Machine.defaults, Atmo.Models.Base.defaults);
