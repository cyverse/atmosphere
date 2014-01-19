define(['react', 'components/identity_select'], function(React, IdentitySelect) {
    var InstanceList = React.createClass({
        render: function() {
            var instances = this.props.instances.map(function(model) {
                return React.DOM.li({}, model.get('name'));
            });

            return React.DOM.ul({}, instances);
        }
    });

    var Instances = React.createClass({
        getInitialState: function() {
            return {
                identity: this.props.profile.get('identities').at(0)
            };
        },
        updateIdentity: function(model, coll) {
            this.setState({identity: identity});
        },
        startListening: function(identity) {
            var instances = identity.get('instances');

            instances.on('sync', this.updateIdentity);
            instances.fetch();
        },
        onSelect: function(identity) {
            this.startListening(identity);
            this.setState({identity: identity});
        },
        componentDidMount: function() {
            this.startListening(this.state.identity);
        },
        componentWillUnmount: function() {
            this.state.identity.get('instances').off('sync', this.updateIdentity);
        },
        render: function() {
            var instances = this.state.identity.get('instances');

            return React.DOM.div({},
                React.DOM.h1({}, "Instances"),
                IdentitySelect({identities: this.props.profile.get('identities'), onSelect: this.onSelect}),
                React.DOM.h2({}, "Provider " + this.state.identity.get('provider_id') + ", Identity " + this.state.identity.get('id')),
                InstanceList({instances: instances})
            );
        }
    });

    return Instances;
});
