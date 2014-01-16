define(['react'], function(React) {
    var Instances = React.createClass({
        render: function() {
            return React.DOM.div({},
                React.DOM.h1({}, "Instances"),
                React.DOM.p({}, "These ur instances"),
                React.DOM.p({}, this.props.profile.get('userid')) 
            );
        }
    });

    return Instances;
});
