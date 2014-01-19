define(['react', 'underscore', 'components/header', 'components/sidebar', 
        'components/footer', 'components/notifications'],
function (React, _, Header, Sidebar, Footer, Notifications) {

    var sidebar_items = {
        dashboard: {
            text: 'Dashboard',
            icon: 'home',
            requires: ['components/dashboard'],
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
            requires: ['components/instances'],
            getView: function(Instances) {
                return Instances({"profile": this.props.profile});
            },
            login_required: true
        },
        volumes: {
            text: 'Volumes',
            icon: 'hdd',
            login_required: true,
            requires: ['components/volumes'],
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
            var modules = sidebar_items[item]._modules;
            if (modules === 'loading')
                return;
            if (modules !== undefined)
                this.setState({active: item, loading: false});
            else {
                sidebar_items[item]._modules = 'loading';
                require(sidebar_items[item].requires, function() {
                    sidebar_items[item]._modules = arguments;
                    this.setState({active: item, loading: false});
                }.bind(this));
            }
        },
        render: function() {
            var view;
            if (this.state.active && !this.state.loading)
                view = sidebar_items[this.state.active].getView.apply(this, sidebar_items[this.state.active]._modules);
            else
                view = React.DOM.div({className: 'loading'});

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
