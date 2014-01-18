define(['backbone'], function(Backbone) {
    var Router = Backbone.Router.extend({
        routes: {
        },
        initialize: function(options) {
            this.app = options.app;
            var base_routes = [
                'dashboard',
                'app_store',
                'instances',
                'volumes',
                'images',
                'providers',
                'quotas',
                'settings',
                'help'
            ];
            var base_route = new RegExp("(" + base_routes.join("|") + ")");
            this.route(base_route, "toggleAppView");
        },
        toggleAppView: function(query) {
            this.app.handleSelect(query);
        }
    });

    return Router;
});
