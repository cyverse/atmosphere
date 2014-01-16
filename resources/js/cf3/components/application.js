define(['react', 'components/header', 'components/sidebar', 'components/footer', 'components/dashboard', 'components/instances'], function (React, Header, Sidebar, Footer, Dashboard, Instances) {
    var sidebar_items = {
        dashboard: {
            text: 'Dashboard',
            icon: 'home',
            view: Dashboard
        },
        app_store: {
            text: 'App Store',
            icon: 'shopping-cart'
        },
        instances: {
            text: 'Instances',
            icon: 'cloud-download',
            view: Instances
        },
        volumes: {
            text: 'Volumes',
            icon: 'hdd'
        },
        images: {
            text: 'Images',
            icon: 'camera'
        },
        providers: {
            text: 'Cloud Providers',
            icon: 'cloud'
        },
        quota: {
            text: 'Quotas',
            icon: 'tasks'
        },
        settings: {
            text: 'Settings',
            icon: 'cog'
        },
        help: {
            text: 'Help',
            icon: 'question-sign'
        }
    };

    var Application = React.createClass({
        getInitialState: function() {
            return {active: 'dashboard'};
        },
        handleSelect: function(item) {
            this.setState({active: item});
        },
        render: function() {
            var view = sidebar_items[this.state.active].view || Dashboard;
            return React.DOM.div({},
                Header(),
                Sidebar({
                    items: sidebar_items, 
                    active: this.state.active,
                    onSelect: this.handleSelect
                }),
                React.DOM.div({'id': 'main'}, view()),
                Footer()
            );
        }
    });

    return Application;
});
