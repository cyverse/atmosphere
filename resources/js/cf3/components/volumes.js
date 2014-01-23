define(['react', 'components/identity_select', 'backbone', 'utils', 
    'components/page_header', 'components/relative_time', 'components/glyphicon',
    'components/button_group'],
    function(React, IdentitySelect, Backbone, Utils, PageHeader, RelativeTime, 
        Glyphicon, ButtonGroup) {

    var Volume = React.createClass({
        render: function() {
            var attach_info = [];
            if (this.props.volume.get('status') == 'attaching')
                attach_info = "Attaching";
            else if (this.props.volume.get('status') == 'detaching')
                attach_info = "Detaching";
            else if (this.props.volume.get('status') == 'in-use')
                attach_info = [
                    "Device location: ",
                    React.DOM.code({}, this.props.volume.get('attach_data').device),
                    React.DOM.br(),
                    "Attached: ",
                    RelativeTime({date: this.props.volume.get('attach_data').attachTime})
                ];


            return React.DOM.li({},
                Glyphicon({name: 'hdd'}),
                React.DOM.div({className: 'volume-header clearfix'}, 
                    React.DOM.strong({}, 
                        this.props.volume.get('name_or_id')
                    ),
                    " (" + this.props.volume.get('size') + " GB)",
                    ButtonGroup({text: 'Actions', actions: {
                        'Detach': null,
                        'Attach': null,
                        'Report as Broken': null,
                    }})
                ),
                "Created: ",
                RelativeTime({date: this.props.volume.get('create_time')}),
                React.DOM.br(),
                attach_info
            );
        }
    });

    var VolumeList = React.createClass({
        render: function() {
            console.log(this.props.volumes);
            var list_items = this.props.volumes.map(function(volume) {
                return Volume({volume: volume})
            });

            if (list_items.length)
                return React.DOM.ul({id: 'volume-list'}, list_items);
            else
                return React.DOM.div({}, "No volumes");
        }
    });

    var Button = React.createClass({
        getDefaultProps: function() {
            return {type: 'default'};
        },
        render: function() {
            return React.DOM.a({className: 'btn btn-' + this.props.type}, this.props.children);
        }
    });

    var Volumes = React.createClass({
        getInitialState: function() {
            return {
                identity: this.props.profile.get('identities').at(0)
            };
        },
        setIdentity: function() {
            this.setState({identity: this.state.identity});
        },
        onSelect: function(identity) {
            this.state.identity.get('volumes').off('sync', this.setIdentity);
            identity.get('volumes').on('sync', this.setIdentity);
            this.setState({identity: identity}, function() {
                identity.get('volumes').fetch();
            });
        },
        render: function() {
            return React.DOM.div({style: {display: this.props.visible ? 'block' : 'none'}},
                PageHeader({title: "Volumes"}),
                IdentitySelect({
                    identities: this.props.profile.get('identities'), 
                    onSelect: this.onSelect,
                    selected: this.state.identity}),
                React.DOM.div({id: 'volume-controls'},
                    Button({onClick: this.showCreateVolumeModal, type: 'primary'}, "Create Volume")
                ),
                //React.DOM.h2({}, "Provider " + this.state.identity.get('provider_id') + ", Identity " + this.state.identity.get('id')),
                VolumeList({volumes: this.state.identity.get('volumes')})
            );
        },
        componentDidMount: function() {
            this.state.identity.get('volumes').on('sync', this.setIdentity);
            this.state.identity.get('volumes').fetch();
        }
    });

    return Volumes;
});
