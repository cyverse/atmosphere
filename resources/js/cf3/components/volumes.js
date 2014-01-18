define(['react', 'components/identity_select', 'backbone', 'views/volume_screen/volume_screen', 'utils'], function(React, IdentitySelect, Backbone, VolumeScreen, Utils) {

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

            return React.DOM.div({},
                React.DOM.h1({}, "Volumes"),
                IdentitySelect({identities: this.props.profile.get('identities'), onSelect: this.onSelect}),
                React.DOM.h2({}, "Provider " + this.state.identity.get('provider_id') + ", Identity " + this.state.identity.get('id')),
                React.DOM.div({id: 'volume-screen'})
            );
        },
        drawVolumeScreen: function() {
            new VolumeScreen({
                el: document.getElementById('volume-screen'),
                volumes: this.state.identity.get('volumes'),
                instances: this.state.identity.get('instances')
            }).render();
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
