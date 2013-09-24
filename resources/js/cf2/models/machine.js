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
	},
    icon: function(size) {
        var size = size || 50;
        if (this.get('icon'))
            return this.get('icon');
        else
            return Atmo.profile.get_icon(this.get('alias_hash'), size);
    }
});

_.extend(Atmo.Models.Machine.defaults, Atmo.Models.Base.defaults);
