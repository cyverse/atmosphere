define(['react', 'components/identity_select', 'backbone', 'views/volume_screen/volume_screen', 'utils', 'components/page_header'], function(React, IdentitySelect, Backbone, VolumeScreen, Utils, PageHeader) {

    var Volumes = React.createClass({
        getInitialState: function() {
            return {
                identity: this.props.profile.get('identities').at(0)
            };
        },
        onSelect: function(identity) {
            this.setState({identity: identity});
        },
        render: function() {

            return React.DOM.div({style: {display: this.props.visible ? 'block' : 'none'}},
                PageHeader({title: "Volumes"}),
                IdentitySelect({identities: this.props.profile.get('identities'), onSelect: this.onSelect}),
                React.DOM.h2({}, "Provider " + this.state.identity.get('provider_id') + ", Identity " + this.state.identity.get('id')),
                React.DOM.div({id: 'volume-screen'})
            );
        },
        drawVolumeScreen: function() {
            new VolumeScreen({
                el: document.getElementById('volume-screen'),
                identity: this.state.identity,
                profile: this.props.profile
            }).render();

            this.state.identity.get('volumes').fetch();
            this.state.identity.get('instances').fetch();
        },
        componentDidMount: function(node) {
            this.drawVolumeScreen();
        },
        componentDidUpdate: function(prevProps, prevState, root) {
            this.drawVolumeScreen();
        }
    });

    return Volumes;
});
