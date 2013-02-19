Atmo.Models.Identity = Atmo.Models.Base.extend(
  {
    defaults: { 'model_name': 'identity' },
	initialize: function(attributes, options) {
		attributes.quota.mem *= 1024;
	},
    parse: function(response) {
      console.log("RESPONSE",response);
      var attributes = response;
      attributes.id = response.id;
      attributes.provider = response.provider;
      attributes.credentials = response.credentials;
	  attributes.quota = response.quota;
	  attributes.quota.mem = response.quota.mem * 1024;
	  attributes.quota.cpu = response.quota.cpu;
	  attributes.quota.disk = response.quota.disk;
	  attributes.quota.disk_count = response.quota.disk_count;
      return attributes;
    },
    url: function(){
      var creds = Atmo.get_credentials();
      return url = this.urlRoot
        + "/provider/" + creds.provider_id 
        + "/" + this.defaults.model_name + "/";
    }
  });

_.extend(Atmo.Models.Identity.defaults, Atmo.Models.Base.defaults);

