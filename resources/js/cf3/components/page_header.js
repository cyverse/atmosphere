define(['react'], function(React) {

    var PageHeader = React.createClass({
        render: function() {
            return React.DOM.div({className: 'main-page-header'},
                React.DOM.h1({}, this.props.title)
            );
        }
    });

    return PageHeader;
});
