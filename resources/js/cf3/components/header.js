define(['react', 'profile'], function(React, profile) {

    var LoginLink = React.createClass({
        render: function() {
            return React.DOM.a({'href': '/login'}, "Login");
        }
    });

    var LogoutLink = React.createClass({
        render: function() {
            return React.DOM.a({'href': '/logout'}, "Logout " + profile.get('username'));
        }
    });

    var Header = React.createClass({
        render: function() {

            var rightChild = profile ? LogoutLink() : LoginLink();

            return React.DOM.header({'className': 'clearfix'},
                React.DOM.a(
                    {href: '/', id: 'logo'}, 
                    React.DOM.img({
                        src: '/resources/images/mini_logo.png', 
                        alt: 'iPlant Cloud Services',
                        height: '30',
                        width: '30'
                    }), 
                    "Atmosphere ",
                    React.DOM.span({id: 'tagline'}, "iPlant Cloud Services")
                ),
                React.DOM.div({id: 'header-nav'}, rightChild)
            );
        }
    });

    return Header;

});
