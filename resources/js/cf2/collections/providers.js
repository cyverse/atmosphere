Atmo.Collections.Providers = Atmo.Collections.Base.extend({
	model: Atmo.Models.Provider,
	url: function(){
		return url = this.urlRoot
			+ '/' + this.model.prototype.defaults.model_name + '/';
	}
});
