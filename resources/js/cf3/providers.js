/*
 * Providers singleton
 */
define(['collections/providers'], function(Providers) {

    var providers = new Providers();
    providers.fetch({async: false});
    return providers;

});
