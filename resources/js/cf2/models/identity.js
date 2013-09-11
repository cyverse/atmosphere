Atmo.Models.Identity = Atmo.Models.Base.extend({
	defaults: { 'model_name': 'identity' },
	initialize: function(attributes, options) {
		attributes.quota.mem *= 1024;
	},
	parse: function(response) {
		var attributes = response;
		
		attributes.id = response.id;
		attributes.provider_id = response.provider_id;
		//attributes.credentials = response.credentials;
		attributes.quota = response.quota;
		attributes.quota.mem = response.quota.mem * 1024;
		attributes.quota.cpu = response.quota.cpu;
		attributes.quota.disk = response.quota.disk;
		attributes.quota.disk_count = response.quota.disk_count;

		// Determine whether this identity is the user's selected identity
		attributes.selected = (Atmo.profile.get('selected_identity').get('id') == attributes.id) ? true : false;

		// Handy reference to corresponding provider model
		attributes.provider = _.filter(Atmo.providers.models, function(provider) {
			return provider.get('id') == attributes.provider_id;
		});
		attributes.provider = attributes.provider[0];
		
		return attributes;
	},
    has_allocation: function() {
        return ( typeof this.attributes.quota.allocation != 'undefined')
    },
	url: function() {
		var creds = Atmo.get_credentials();
		return url = this.urlRoot
			+ '/provider/' + creds.provider_id 
			+ '/' + this.defaults.model_name + '/';
	}
});

_.extend(Atmo.Models.Identity.defaults, Atmo.Models.Base.defaults);

