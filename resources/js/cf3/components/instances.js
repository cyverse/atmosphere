define(['react'], function(React) {
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
        render: function() {

            var identities = this.props.profile.get('identities');
            var instance_lists = identities.map(function(identity) {
                var instances = identity.get_instances();
                var list = InstanceList({instances: instances});
                instances.fetch();
                var header = React.DOM.h2({}, "Provider " + identity.get('provider_id') + ", Identity " + identity.get('id'))
                return [header, list];
            });

            return React.DOM.div({},
                React.DOM.h1({}, "Instances"),
                React.DOM.p({}, "These ur instances"),
                instance_lists
            );
        }
    });

    return Instances;
});
