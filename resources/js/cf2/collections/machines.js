/* machines.js
 * Backbone.js machines collection.
 */

Atmo.Collections.Machines = Atmo.Collections.Base.extend({
	model: Atmo.Models.Machine,
    get_featured: function() {
        return new Atmo.Collections.Machines(this.where({featured: true}));
    },
	select_machine: function(model) {
        //console.log("selected", model);
		if (model == null) 
			Backbone.history.navigate('images');
		else {
			Backbone.history.navigate('images/' + model.id);
			this.trigger('select', model);
		}
	}
});
