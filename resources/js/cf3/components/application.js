define(['react', 'underscore', 'components/header', 'components/sidebar', 
        'components/footer', 'components/notifications'],
function (React, _, Header, Sidebar, Footer, Notifications) {

    var sidebar_items = {
        dashboard: {
            text: 'Dashboard',
            icon: 'home',
            modules: ['components/dashboard'],
            getView: function(Dashboard) {
                return Dashboard();
            },
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
            modules: ['components/instances'],
            getView: function(Instances) {
                return Instances({"profile": this.props.profile});
            },
            login_required: true
        },
        volumes: {
            text: 'Volumes',
            icon: 'hdd',
            login_required: true,
            modules: ['components/volumes'],
            getView: function(Volumes) {
                return Volumes({"profile": this.props.profile});
            }
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
        quotas: {
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
                active: null,
                laoding: true
            };
        },
        handleSelect: function(item) {
            /*
             * Lazy load views
             * http://www.bennadel.com/blog/2402-Lazy-Loading-RequireJS-Modules-When-They-Are-First-Requested.htm
             */
            Backbone.history.navigate(item);
            if (!sidebar_items[item])
                throw 'invalid route ' + item;
            this.setState({loading: true, active: item});
            var view = sidebar_items[item].view;
            if (view === 'loading')
                return;
            if (view !== undefined)
                this.setState({active: item});
            else {
                sidebar_items[item].view = 'loading';
                require(sidebar_items[item].modules, function() {
                    sidebar_items[item].view = sidebar_items[item].getView.apply(this, arguments);
                    window.setTimeout(function() {
                        this.setState({active: item, loading: false});
                    }.bind(this), 2000);
                }.bind(this));
            }
        },
        render: function() {
            var view;
            if (this.state.active && !this.state.loading)
                view = sidebar_items[this.state.active].view;
            else
                view = React.DOM.div({}, "loading");

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
                Notifications(),
                React.DOM.div({'id': 'main'}, view),
                Footer()
            );
        }
    });

    return Application;
});
