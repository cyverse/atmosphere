define(['underscore', 'models/base', 'collections/instances'], function(_, Base, Instances) {
    var Identity = Base.extend({
        defaults: { 'model_name': 'identity' },
        initialize: function(attributes, options) {
            attributes.quota.mem *= 1024;
        },
        parse: function(response) {
            var attributes = response;
            
            attributes.id = response.id;
            attributes.provider_id = response.provider_id;
            //attributes.credentials = response.credentials;
            attributes.quota = response.quota;
            attributes.quota.mem = response.quota.mem * 1024;
            attributes.quota.cpu = response.quota.cpu;
            attributes.quota.disk = response.quota.disk;
            attributes.quota.disk_count = response.quota.disk_count;

            return attributes;
        },
        has_allocation: function() {
            return ( typeof this.attributes.quota.allocation != 'undefined')
        },
        url: function() {
            var creds = Atmo.get_credentials();
            return url = this.urlRoot
                + '/provider/' + creds.provider_id 
                + '/' + this.defaults.model_name + '/';
        },
        /*
         * Overriding get for caching collections
         */
        get: function(attr) {
            if (typeof this[attr] == 'function')
                return this[attr]();
            return Backbone.Model.prototype.get.call(this, attr);
        },
        instances: function() {
            var instances = this.get('_instances');
            if (!instances) {
                instances = new Instances(null, {
                    provider_id: this.get('provider_id'),
                    identity_id: this.id
                });
                this.set('_instances', instances);
            }
            return instances;
        }
    });

    _.extend(Identity.defaults, Base.defaults);

    return Identity;
});
