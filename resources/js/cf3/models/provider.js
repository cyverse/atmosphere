define(['underscore', 'models/base'], function(_, Base) {

    var Provider = Base.extend({
        defaults: { 'model_name': 'provider' },
        parse: function(response) {
            var attributes = response;
            
            attributes.id = response.id;
            attributes.location = response.location;
            attributes.public = response.public;
            
            return attributes;
        },
        url: function(){
            var url = this.urlRoot
                + '/' + this.defaults.model_name + '/';
            
            if (typeof this.get('id') != 'undefined') {
                url += this.get('id') + '/';
            }
            
            return url;
        }
    });

    _.extend(Provider.defaults, Base.defaults);

    return Provider;
});
