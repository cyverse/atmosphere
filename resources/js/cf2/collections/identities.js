Atmo.Collections.Identities = Atmo.Collections.Base.extend({
	model: Atmo.Models.Identity,
	url: function(){
		return url = this.urlRoot
			+ '/' + this.model.prototype.defaults.model_name + '/';
	}
});
