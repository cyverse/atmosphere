define(['react', 'underscore', 'components/header', 'components/sidebar', 
        'components/footer', 'components/notifications'],
function (React, _, Header, Sidebar, Footer, Notifications) {

    var Application = React.createClass({
        getDefaultProps: function() {
            return {pages: {
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
                        return Instances({profile: this.props.profile});
                    },
                    login_required: true
                },
                volumes: {
                    text: 'Volumes',
                    icon: 'hdd',
                    login_required: true,
                    requires: ['components/volumes'],
                    getView: function(Volumes) {
                        return Volumes({profile: this.props.profile});
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
            }};
        },
        getInitialState: function() {
            var rendered = _.chain(this.props.pages)
                .map(function(v, k) {
                    return [k, false];
                }).object().value();

            return {
                active: null,
                laoding: true,
                rendered: rendered
            };
        },
        handleSelect: function(item) {
            /*
             * Lazy load views
             * http://www.bennadel.com/blog/2402-Lazy-Loading-RequireJS-Modules-When-They-Are-First-Requested.htm
             */
            Backbone.history.navigate(item);
            if (!this.props.pages[item])
                throw 'invalid route ' + item;

            var modules = this.props.pages[item]._modules;
            if (modules === 'loading')
                return;
            if (modules !== undefined)
                this.setState({active: item, loading: false});
            else {
                this.props.pages[item]._modules = 'loading';
                this.setState({loading: true, active: item}, function() {
                    require(this.props.pages[item].requires, function() {
                        this.props.pages[item]._modules = arguments;
                        var rendered = this.state.rendered;
                        rendered[item] = true;
                        this.setState({rendered: rendered, active: item, loading: false});
                    }.bind(this));
                }.bind(this));
            }
        },
        getPages: function() {
            /*
             * We keep every page's view alive at all times. We just hide all 
             * but the active one
             */
            var view = [React.DOM.div({className: 'loading', style: {display: this.state.loading ? 'block' : 'none'}, key: 'loading'})];
            var screens = _.chain(this.state.rendered)
                .map(function(rendered, k) {
                    var modules = this.props.pages[k]._modules;
                    if (rendered && modules && modules != 'loading') {
                        var v = this.props.pages[k].getView.apply(this, modules);
                        v.props.key = k;
                        v.props.id = k + '-page';
                        v.props.visible = k == this.state.active;
                        return v;
                    } else {
                        return React.DOM.div({key: k});
                    }
                }.bind(this))
                .value();
            view = view.concat(screens);
            return view;
        },
        render: function() {
            var pages = this.getPages();
            var items = this.props.pages;
            if (this.props.profile == null)
                items = _.chain(this.props.pages)
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
                React.DOM.div({'id': 'main'}, pages),
                Footer()
            );
        }
    });

    return Application;
});
