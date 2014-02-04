define(['react', 'underscore', 'bootstrap'], function(React, _, Bootstrap) {
    var ButtonGroup = React.createClass({
        render: function() {
            return React.DOM.div({className: 'btn-group'},
                React.DOM.button({
                    type: 'button', 
                    className: 'btn btn-default dropdown-toggle', 
                    'data-toggle': 'dropdown'},
                    this.props.text,
                    " ",
                    React.DOM.span({className: 'caret'})
                ),
                React.DOM.ul({className: 'dropdown-menu', role: 'menu'},
                    _.map(this.props.actions, function(callback, text) {
                        return React.DOM.li({}, 
                            React.DOM.a({href: '#', onClick: callback}, text)
                        );
                    })
                )
            );
        }
    }); 

    return ButtonGroup;
});
