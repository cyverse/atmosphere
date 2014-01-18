/* volumes.js
 * Backbone.js volumes collection.
 */
define(['underscore', 'collections/base', 'models/volume'], function(_, Base, Volume) {

var Volumes = Base.extend({
    model: Volume,
    initialize: function(models, options) {
        this.creds = _.pick(options, 'provider_id', 'identity_id');
        this.selected_volume = null;
    },
    // Return the list of available volumes
    get_available: function() {
        return _.filter(this.models, function(model) {
            return model.get('status') == 'available';
        });
    },
    select_volume: function(model) {
        this.selected_volume = model;
        this.trigger('select', model);
    },
    update: function(options) {
        if (!options) options = {};
        if (!options.success) options.success = function() {};
        if (!options.error) options.error = function() {};
        var new_collection = new this.constructor();
        new_collection.url = this.url;
        new_collection.model = this.model;

        var self = this;
        new_collection.fetch({
            force_new: true,
            success: function() {
                var model_ids = self.get_model_id_array();
                var new_model_ids = new_collection.get_model_id_array();

                /* New models */
                _.each(_.difference(new_model_ids, model_ids), function(model_id) {
                    self.add(new_collection.get(model_id).clone());
                });

                /* Models to remove */
                _.each(_.difference(model_ids, new_model_ids), function(model_id) {
                    self.remove(self.get(model_id));
                });

                /* Models to update */
                _.each(_.intersection(model_ids, new_model_ids), function(model_id) {
                    var new_model = new_collection.get(model_id);
                    var old_model = self.get(model_id);
                    var to_update = _.pick(new_model.attributes, 'attach_data_attach_time', 'attach_data_device', 'attach_data_instance_id', 'status');
                    old_model.set(to_update);
                });

                options.success();
            }
        });
    },
    get_model_id_array: function() {
        return _(this.models).map(function (model) {return model.id; });
    }
});

return Volumes;

});
