Atmo.Models.Profile = Atmo.Models.Base.extend({
	defaults: { 'model_name': 'profile' },
	parse: function(response) {
		var attributes = response;
		
		attributes.id = response.username;
		attributes.userid = response.username;
		attributes.ec2_access_key = null;
		attributes.ec2_secret_key = null;
		attributes.ec2_url = null;
		attributes.s3_url = null;
		attributes.token = null;
		attributes.api_server = null;
		attributes.default_vnc = response.vnc_resolution;
		attributes.background = response.background;
		attributes.send_emails = response.send_emails;
		attributes.default_size = response.default_size;
		attributes.quick_launch = response.quick_launch;
		attributes.icon_set = response.icon_set;
		attributes.settings = {};
		attributes.settings.background = response.background;
		attributes.settings.default_size = response.default_size;
		attributes.settings.default_vnc = response.default_vnc;
		attributes.settings.icon_set = response.icon_set;
		attributes.settings.quick_launch = response.quick_launch;
		attributes.settings.send_emails = response.send_emails;
		attributes.selected_identity = new Atmo.Models.Identity(response.selected_identity);
		
		return attributes;
    },
	url: function(){
		return url = this.urlRoot
			+ '/' + this.defaults.model_name + '/';
	},
    // Given a md5 hash, return the URL to a icon
	get_icon: function(hash) {
		var icon_set = this.get('settings')['icon_set'];
        if (icon_set == 'default')
            return "//www.gravatar.com/avatar/" + hash + "?d=identicon&s=50"; 
        if (icon_set == 'unicorn')
            return "//unicornify.appspot.com/avatar/" + hash + "?s=50";
        if (icon_set == 'wavatar')
            return "//www.gravatar.com/avatar/" + hash + "?d=wavatar&s=50";
        if (icon_set == 'monster')
            return "//www.gravatar.com/avatar/" + hash + "?d=monsterid&s=50";
        if (icon_set == 'retro')
            return "//www.gravatar.com/avatar/" + hash + "?d=retro&s=50";
        if (icon_set == 'robot')
            return "//robohash.org/" + hash + "?size=50x50";
        return null;
    }
});

_.extend(Atmo.Models.Profile.defaults, Atmo.Models.Base.defaults);


