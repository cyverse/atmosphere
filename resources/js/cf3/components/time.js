/*
 * Semantic time element
 */
define(['react', 'utils', 'moment'], function(React, Utils, Moment) {

    var Time = React.createClass({
        propTypes: {
            date: React.PropTypes.instanceOf(Date),
            showAbsolute: React.PropTypes.bool,
            showRelative: React.PropTypes.bool
        },
        getDefaultProps: function() {
            return {
                showAbsolute: true,
                showRelative: true
            };
        },
        render: function() {
            var text = "";
            var absoluteText = Moment(this.props.date).format("MMM D, YYYY");
            var relativeText = Utils.relative_time(this.props.date);

            if (this.props.showAbsolute) {
                text += absoluteText;
                if (this.props.showRelative)
                    text += " (" + relativeText + ")";
            } else if (this.props.showRelative) {
                text += relativeText;
            }

            return React.DOM.time({
                title: Moment(this.props.date).format(),
                dateTime: Moment(this.props.date).utc().format()
            }, text);
        }
    });

    return Time;

});
