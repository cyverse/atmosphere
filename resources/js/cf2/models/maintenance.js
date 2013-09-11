Atmo.Models.Maintenance = Atmo.Models.Base.extend({
	defaults: { 'model_name': 'maintenance' },
	url: function(){
		return url = this.urlRoot
			+ '/' + this.defaults.model_name + '/?active=True';
	}
});

_.extend(Atmo.Models.Maintenance.defaults, Atmo.Models.Base.defaults);
