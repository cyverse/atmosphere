/* base.js
 * Backbone.js base collection functionality.
 */
define(['backbone', 'underscore'], function(Backbone, _) {

var Base = Backbone.Collection.extend({
    urlRoot: '/api/v1',
    url: function() {
        var creds = this.creds;
        return url = this.urlRoot
            + '/provider/' + creds.provider_id 
            + '/identity/' + creds.identity_id
            + '/' + this.model.prototype.defaults.model_name + '/';
    },
    defaults: {
        'api_url': '/api/v1',
        'model_name': 'base'
    },
    fetch: function(options) {
        var self = this;
        var opts =  { 
            success: function() {
                if (options && options.success)
                    options.success(self);
            },
            error: function() {
                // Allow views to respond to failed fetch calls
                self.trigger('fail');

                if (options && options.error)
                    options.error(self);
            }    
        };

        // Combine options and custom handlers, apply to fetch prototype.
        (_.bind(Backbone.Collection.prototype.fetch, this, _.extend({}, options, opts)))();
    }
});

return Base;

});
