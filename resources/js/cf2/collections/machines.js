/* machines.js
 * Backbone.js machines collection.
 */

Atmo.Collections.Machines = Atmo.Collections.Base.extend({
	model: Atmo.Models.Machine,
    featured: function() {
        return new Atmo.Collections.Machines(this.where({featured: true}));
    }
});
