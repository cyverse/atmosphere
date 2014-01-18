define(['collections/base', 'models/provider'], function(Base, Provider) {

    return Base.extend({
        model: Provider,
        url: function(){
            return url = this.urlRoot
                + '/' + this.model.prototype.defaults.model_name + '/';
        }
    });

});
