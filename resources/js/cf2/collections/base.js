/* base.js
 * Backbone.js base collection functionality.
 */

Atmo.Collections.Base = Backbone.Collection.extend({
  urlRoot: '/api',
  url: function() {
    var creds = Atmo.get_credentials();
    return url = this.urlRoot
      + "/provider/" + creds.provider_id 
      + "/identity/" + creds.identity_id
      + "/" + this.model.prototype.defaults.model_name + "/";
  },
  defaults: {
    'api_url': '/api',
    'model_name': 'base'
  }
});
