define(['react', 'underscore', 'components/header', 'components/sidebar', 
        'components/footer', 'components/dashboard', 'components/instances'],
function (React, _, Header, Sidebar, Footer, Dashboard, Instances) {
    var sidebar_items = {
        dashboard: {
            text: 'Dashboard',
            icon: 'home',
            view: Dashboard,
            login_required: true
        },
        app_store: {
            text: 'App Store',
            icon: 'shopping-cart',
            login_required: false
        },
        instances: {
            text: 'Instances',
            icon: 'cloud-download',
            view: Instances,
            login_required: true
        },
        volumes: {
            text: 'Volumes',
            icon: 'hdd',
            login_required: true
        },
        images: {
            text: 'Images',
            icon: 'camera',
            login_required: true
        },
        providers: {
            text: 'Cloud Providers',
            icon: 'cloud',
            login_required: true
        },
        quota: {
            text: 'Quotas',
            icon: 'tasks',
            login_required: true
        },
        settings: {
            text: 'Settings',
            icon: 'cog',
            login_required: true
        },
        help: {
            text: 'Help',
            icon: 'question-sign',
            login_required: false
        }
    };

    var Application = React.createClass({
        getInitialState: function() {
            return {
                active: this.props.profile == null ? 'app_store' : 'dashboard'
            };
        },
        handleSelect: function(item) {
            this.setState({active: item});
        },
        render: function() {
            var view = sidebar_items[this.state.active].view || Dashboard;
            var items = sidebar_items;
            if (this.props.profile == null)
                items = _.chain(sidebar_items)
                    .pairs()
                    .filter(function(i) {
                        return !i[1].login_required;
                    })
                    .object()
                    .value();

            return React.DOM.div({},
                Header(),
                Sidebar({
                    items: items, 
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
