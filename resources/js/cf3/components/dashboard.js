define(['react'], function(React) {
    var Dashboard = React.createClass({
        render: function() {
            return React.DOM.div({},
                React.DOM.h1({}, "Dashboard"),
                React.DOM.p({}, "Welcome to Atmosphere!")
            );
        }
    });
    return Dashboard;
});
