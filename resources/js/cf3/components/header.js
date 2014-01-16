define(['react'], function(React) {
    var Header = React.createClass({
        render: function() {
            return React.DOM.header({},
                React.DOM.a(
                    {href: '/'}, 
                    React.DOM.img({
                        src: '/resources/images/mini_logo.png', 
                        alt: 'iPlant Cloud Services',
                        height: '30',
                        width: '30'
                    }, "Atmosphere: iPlant Cloud Services")
                )
            );
        }
    });
    return Header;
});
