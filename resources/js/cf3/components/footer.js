define(['react'], function(React) {
    var Footer = React.createClass({
        render: function() {
            var year = new Date().getFullYear();
            return React.DOM.footer({},
                React.DOM.a({
                    'href': 'http://user.iplantcollaborative.org',
                    'target': '_blank'
                }, "\u00a9" + year + " iPlant Collaborative"));
        }
    });
    return Footer;
});
