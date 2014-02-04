define(['react', 'components/glyphicon'], function(React, Glyphicon) {

    var PageHeader = React.createClass({
        render: function() {
            var help_button = [];
            var help_text = [];
            if (this.props.helpText) {
                help_button = React.DOM.button({
                    type: 'button', 
                    id: 'help-text-toggle-button',
                    className: 'btn btn-default', 
                    'data-toggle': 'collapse',
                    'data-target': '#help-text'},
                    Glyphicon({name: 'question-sign'}));

                help_text = React.DOM.div({
                    id: 'help-text', 
                    className: 'collapse'},
                    React.DOM.div({className: 'well'}, this.props.helpText()));
            }

            return React.DOM.div({className: 'main-page-header'},
                React.DOM.h1({}, this.props.title),
                help_button,
                help_text);
        }
    });

    return PageHeader;
});
