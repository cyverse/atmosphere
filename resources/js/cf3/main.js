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

require(['jquery', 'backbone', 'react'], function($, Backbone, React) {
    $(document).ready(function() {
        var Glyphicon = React.createClass({
            render: function() {
                return React.DOM.i({className: 'glyphicon glyphicon-' + this.props.name});
            }
        });

        var SidebarListItem = React.createClass({
            handleClick: function() {
                this.props.onClick(this.props.text);
            },
            render: function() {
                return React.DOM.li(
                    {className: this.props.active ? 'active' : ''}, 
                    React.DOM.a({href: '#', onClick: this.handleClick}, 
                        Glyphicon({name: this.props.icon}), 
                        this.props.text
                    )
                );
            }
        });

        var Sidebar = React.createClass({
            getInitialState: function() {
                return {active: this.props.active};
            },
            onClick: function(clicked) {
                this.setState({active: clicked});
            },
            render: function() {
                var self = this;
                var items = _.map(this.props.items, function(item) {
                    return SidebarListItem({
                        icon: item[1], 
                        active: item[0] == self.state.active,
                        onClick: self.onClick,
                        text: item[0]
                    });
                });
                return React.DOM.ul({}, items);
            }
        });

        var sidebar_items = [
            ['Dashboard', 'home'],
            ['App Store', 'shopping-cart'],
            ['Instance', 'cloud-download'],
            ['Volumes', 'hdd'],
            ['Images', 'camera'],
            ['Cloud Providers', 'cloud'],
            ['Quotas', 'tasks'],
            ['Settings', 'cog'],
            ['Help', 'question-sign']
        ];
        React.renderComponent(Sidebar({items: sidebar_items, active: 'Dashboard'}), document.getElementById('sidebar'));
        console.log('test'); 
        console.log(Backbone);
    });
});
