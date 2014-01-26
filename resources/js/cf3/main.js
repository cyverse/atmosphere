require.config({
    baseUrl: '/resources/js/cf3',
    paths: {
        'jquery': '//ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery',
        'backbone': '//cdnjs.cloudflare.com/ajax/libs/backbone.js/1.1.0/backbone-min',
        'underscore': '//cdnjs.cloudflare.com/ajax/libs/underscore.js/1.4.3/underscore-min',
        'google': 'https://www.google.com/jsapi',
        'bootstrap': '//cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.0.3/js/bootstrap.min',
        'moment': '//cdnjs.cloudflare.com/ajax/libs/moment.js/2.5.0/moment.min',
        'react': '//cdnjs.cloudflare.com/ajax/libs/react/0.8.0/react'
    },
    shim: {
        backbone: {
            deps: ['underscore', 'jquery'],
            exports: 'Backbone'
        },
        underscore: {
            exports: '_'
        },
        bootstrap: {
            deps: ['jquery']
        }
    }
});

require(['jquery', 'backbone', 'react', 'components/application', 'models/profile', 'collections/identities', 'router'], function($, Backbone, React, Application, Profile, Identities, Router) {
    /* Get Profile and identities beofre we do anything else  */
    /* TODO: To this server side */
    var profile = new Profile();
    profile.fetch({
        async: false,
        success: function(model) {
            var identities = new Identities();
            identities.fetch({
                async: false
            });

            model.set('identities', identities);
        },
        error: function(model, response, options) {
            if (response.status == 401) {
                console.log("Not logged in");
            } else {
                console.error("Error fetching profile");
            }
        }
    });

    var logged_in = !profile.isNew();

    $(document).ready(function() {
        var app = Application({profile: logged_in ? profile : null});
        React.renderComponent(app, document.getElementById('application'));

        var route = logged_in ? 'dashboard' : 'app_store';
        new Router({app: app, defaultRoute: route});
        Backbone.history.start({
            pushState: true,
            root: url_root
        });
    });
});
