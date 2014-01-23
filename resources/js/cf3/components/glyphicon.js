define(['react'], function(React) {

    var Glyphicon = React.createClass({
        render: function() {
            return React.DOM.i({className: 'glyphicon glyphicon-' + this.props.name});
        }
    });

    return Glyphicon;

});
