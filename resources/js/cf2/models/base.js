/* base.js
 * Backbone.js base model functionality.
 */

Atmo.Models.Base = Backbone.Model.extend({
  defaults: {
    'model_name': 'base'
  },
  urlRoot: '/api',
  url: function(){
    var creds = Atmo.get_credentials();
    var url = this.urlRoot
      + "/provider/" + creds.provider_id 
      + "/identity/" + creds.identity_id
      + "/" + this.defaults.model_name + "/";
    console.log(this)
    if ( typeof this.get('id') != 'undefined') {
      url += this.get('id') + "/";
    }
    return url;
  }
});

