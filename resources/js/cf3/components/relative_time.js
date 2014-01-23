/*
 * Semantic time element
 */
define(['react', 'utils', 'moment'], function(React, Utils, Moment) {

    /*
     * Props: (Date) date
     */
    var RelativeTime = React.createClass({
        render: function() {
            console.log(this.props);
            console.log(this.props.date);
            return React.DOM.time({
                title: Moment(this.props.date).format(),
                dateTime: Moment(this.props.date).utc().format()
            }, Utils.relative_time(this.props.date));
        }
    });

    return RelativeTime;

});
