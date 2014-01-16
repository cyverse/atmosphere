define(['react', 'components/header', 'components/sidebar', 'components/footer', 'components/dashboard'], function (React, Header, Sidebar, Footer, Dashboard) {
    var sidebar_items = {
        dashboard: {
            text: 'Dashboard',
            icon: 'home'
        },
        app_store: {
            text: 'App Store',
            icon: 'shopping-cart'
        },
        instances: {
            text: 'Instances',
            icon: 'cloud-download'
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
        /*
        ['Dashboard', 'home'],
        ['App Store', 'shopping-cart'],
        ['Instances', 'cloud-download'],
        ['Volumes', 'hdd'],
        ['Images', 'camera'],
        ['Cloud Providers', 'cloud'],
        ['Quotas', 'tasks'],
        ['Settings', 'cog'],
        ['Help', 'question-sign']
        */
    };

    var Application = React.createClass({
        getInitialState: function() {
            return {active: 'dashboard'};
        },
        handleSelect: function(item) {
            //console.log(item);
        },
        render: function() {
            return React.DOM.div({},
                Header(),
                Sidebar({
                    items: sidebar_items, 
                    active: this.state.active,
                    onSelect: this.handleSelect
                }),
                React.DOM.div({'id': 'main'}, Dashboard()),
                Footer()
            );
        }
    });

    return Application;
});
