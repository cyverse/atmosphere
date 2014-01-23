define(['react', 'components/identity_select', 'backbone', 'utils', 
    'components/page_header', 'components/relative_time', 'components/glyphicon',
    'components/button_group', 'components/modal'],
    function(React, IdentitySelect, Backbone, Utils, PageHeader, RelativeTime, 
        Glyphicon, ButtonGroup, Modal) {

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

    var VolumeControls = React.createClass({
        render: function() {
            return React.DOM.div({id: 'volume-controls'},
                React.DOM.button({
                    className: 'btn btn-primary',
                    'data-target': '#volume-create-modal',
                    'data-toggle': 'modal'
                    }, "Create Volume"),
                Modal({id: 'volume-create-modal', title: "New Volume"},
                    React.DOM.div({className: 'modal-body'}, 'make a new volume and stuff'),
                    React.DOM.div({className: 'modal-footer'}, 'yeah')))
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
                VolumeControls({identity: this.state.identity}),
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
