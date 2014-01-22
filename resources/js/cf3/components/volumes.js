define(['react', 'components/identity_select', 'backbone', 'utils', 
    'components/page_header'], 
    function(React, IdentitySelect, Backbone, Utils, PageHeader) {

    var VolumeList = React.createClass({
        render: function() {
            var list_items = this.props.volumes.map(function(volume) {
                return React.DOM.li({},
                    volume.get('name_or_id') + " (" + volume.get('size') + " GB)",
                    "Created: " + volume.get('start_date'));
            }.bind(this));

            if (list_items.length)
                return React.DOM.ul({id: 'volume-list'}, list_items);
            else
                return React.DOM.div({}, "No volumes");
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
                IdentitySelect({identities: this.props.profile.get('identities'), onSelect: this.onSelect}),
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
