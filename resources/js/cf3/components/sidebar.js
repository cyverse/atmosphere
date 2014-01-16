define(['react', 'underscore'], function (React, _) {
    var Glyphicon = React.createClass({
        render: function() {
            return React.DOM.i({className: 'glyphicon glyphicon-' + this.props.name});
        }
    });

    var SidebarListItem = React.createClass({
        handleClick: function() {
            this.props.onClick(this.props.id);
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
            this.props.onSelect(clicked);
            this.setState({active: clicked});
        },
        render: function() {
            var items = _.map(this.props.items, function(item, id) {
                return SidebarListItem({
                    icon: item.icon, 
                    active: id == this.state.active,
                    onClick: this.onClick,
                    text: item.text,
                    id: id
                });
            }.bind(this));
            return React.DOM.div({id: 'sidebar'}, React.DOM.ul({}, items));
        }
    });

    return Sidebar;
});
