/*
 * Semantic time element
 */
define(['react', 'utils', 'moment'], function(React, Utils, Moment) {

    var RelativeTime = React.createClass({
        propTypes: {
            date: React.PropTypes.instanceOf(Date)
        },
        render: function() {
            return React.DOM.time({
                title: Moment(this.props.date).format(),
                dateTime: Moment(this.props.date).utc().format()
            }, Utils.relative_time(this.props.date));
        }
    });

    return RelativeTime;

});
