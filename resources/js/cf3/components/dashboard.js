define(['react', 'underscore'], function(React, _) {
    var DashboardIcon = React.createClass({
        render: function() {
            return React.DOM.li({}, 
                React.DOM.img({src: this.props.image}),
                React.DOM.strong({}, this.props.title),
                React.DOM.p({}, this.props.description)
            );
        }
    });

    var items = [
        {
            image: '/resources/images/icon_launchnewinstance.png',
            title: 'Launch New Instance',
            description: 'Browse Atmosphere\'s list of available images and select one to launch a new instance.',
            href: 'app_store'
        },
        {
            image: '/resources/images/icon_gethelp.png',
            title: 'Browse Help Resources',
            description: 'View a video tutorial, read the how-to guides, or email the Atmosphere support team.',
            href: 'help'
        },
        {
            image: '/resources/images/icon_settings.png',
            title: 'Change Your Settings',
            description: 'Modify your account settings, view your resource quota, or request more resources.',
            href: 'settings'
        }
    ];

    var Dashboard = React.createClass({
        render: function() {
            return React.DOM.div({},
                React.DOM.h1({}, "Dashboard"),
                React.DOM.p({}, "Welcome to Atmosphere!"),
                React.DOM.ul({}, _.map(items, DashboardIcon))
            );
        }
    });

    return Dashboard;
});
