require.config({
    baseUrl: '/resources/js/cf3',
    paths: {
        'jquery': '//ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery',
        'backbone': '//cdnjs.cloudflare.com/ajax/libs/backbone.js/0.9.9/backbone-min',
        'underscore': '//cdnjs.cloudflare.com/ajax/libs/underscore.js/1.4.3/underscore-min',
        'google': 'https://www.google.com/jsapi',
        'bootstrap': '//cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.0.3/js/bootstrap.min',
        'date': '//cdnjs.cloudflare.com/ajax/libs/datejs/1.0/date.min',
        'react': '//cdnjs.cloudflare.com/ajax/libs/react/0.8.0/react.min'
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

require(['jquery', 'backbone', 'react', 'components/application'], function($, Backbone, React, Application) {
    $(document).ready(function() {

        React.renderComponent(Application(), document.getElementById('application'));
    });
});
