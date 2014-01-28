define(['react', 'notifications', 'jquery'], function(React, notifications, $) {

    // Number of milliseconds to display a notification
    var timeout = 10 * 1000;

    var Notifications = React.createClass({
        getInitialState: function() {
            return {model: null};
        },
        componentWillMount: function() {
            notifications.bind('add', function(model) {
                this.setState({model: model});
            }, this);
        },
        render: function() {
            var content = [];
            if (this.state.model)
                content = React.DOM.div({className: 'alert alert-'+this.state.model.get('type')+' fade in'},
                    React.DOM.button({className: 'close', 'data-dismiss': 'alert'},
                        '\u00d7'
                    ),
                    React.DOM.strong({}, this.state.model.get('header')),
                    " ",
                    React.DOM.span({dangerouslySetInnerHTML: {'__html': this.state.model.get('body') }})
                )
            return React.DOM.div({id: 'notifications'}, content);
        },
        componentDidUpdate: function(prevProps, prevState, root) {
            if (!this.state.model)
                return;
            if (!this.state.model.get('sticky'))
                setTimeout(function() {
                    $('.close').trigger('click');
                }, timeout);
        }
    });

    return Notifications;
});
