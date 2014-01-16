define(['react', 'components/identity_select'], function(React, IdentitySelect) {
    var InstanceList = React.createClass({
        getInitialState: function() {
            return {instances: this.props.instances};
        },
        componentWillMount: function() {
            this.props.instances.bind('add', function(model, coll) {
                this.setState({instances: coll}); 
            }.bind(this));
        },
        render: function() {
            var instances = this.state.instances.map(function(model) { 
                return React.DOM.li({}, model.get('name'));
            });

            return React.DOM.ul({}, instances);
        }
    });

    var Instances = React.createClass({
        getInitialState: function() {
            return {identity: this.props.profile.get('identities').at(0)};
        },
        onSelect: function(identity) {
            this.setState({identity: identity});
        },
        render: function() {

            var instances = this.state.identity.get_instances();
            instances.fetch();

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
