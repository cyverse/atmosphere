require.config({
    baseUrl: '/resources/js/cf3',
    paths: {
        /* TODO: use minified versions in production */
        'jquery': '//cdnjs.cloudflare.com/ajax/libs/jquery/2.1.0/jquery',
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

require(['jquery', 'backbone', 'react', 'components/application', 'profile', 'router'], function($, Backbone, React, Application, profile, Router) {

    $(document).ready(function() {
        var app = Application();
        React.renderComponent(app, document.getElementById('application'));

        var route = profile != null ? 'dashboard' : 'app_store';
        new Router({app: app, defaultRoute: route});
        Backbone.history.start({
            pushState: true,
            root: url_root
        });
    });

});
