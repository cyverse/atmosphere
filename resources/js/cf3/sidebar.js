define(['react'], function (React) {
    var Glyphicon = React.createClass({
        render: function() {
            return React.DOM.i({className: 'glyphicon glyphicon-' + this.props.name});
        }
    });

    var SidebarListItem = React.createClass({
        handleClick: function() {
            this.props.onClick(this.props.text);
        },
        render: function() {
            return React.DOM.li(
                {className: this.props.active ? 'active' : ''}, 
                React.DOM.a({href: '#', onClick: this.handleClick}, 
                    Glyphicon({name: this.props.icon}), 
                    this.props.text
                )
            );
        }
    });

    var Sidebar = React.createClass({
        getInitialState: function() {
            return {active: this.props.active};
        },
        onClick: function(clicked) {
            this.setState({active: clicked});
        },
        render: function() {
            var self = this;
            var items = _.map(this.props.items, function(item) {
                return SidebarListItem({
                    icon: item[1], 
                    active: item[0] == self.state.active,
                    onClick: self.onClick,
                    text: item[0]
                });
            });
            return React.DOM.ul({}, items);
        }
    });

    return Sidebar;
});
