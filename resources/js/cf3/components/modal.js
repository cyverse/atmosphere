define(['react', 'bootstrap'], function(React) {

    var Modal = React.createClass({
        render: function() {
            return React.DOM.div({
                id: this.props.id,
                className: 'modal fade',
                tabindex: '-1',
                role: 'dialog',
                'aria-hidden': 'true'
                },
                React.DOM.div({className: 'modal-dialog'},
                    React.DOM.div({className: 'modal-content'},
                        React.DOM.div({className: 'modal-header'},
                            React.DOM.button({
                                type: 'button',
                                className: 'close',
                                'data-dismiss': 'modal',
                                'aria-hidden': 'true'
                                }, '\u00d7'),
                            React.DOM.h4({
                                className: 'modal-title'
                                }, this.props.title)),
                        this.props.children)));
        }
    });

    return Modal;
});
