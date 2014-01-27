define(['react', 'profile'], function(React, profile) {

    var Icon = React.createClass({
        propTypes: {
            hash: React.PropTypes.string
        },
        getSrc: function(hash, icon_set) {
            if (icon_set == 'default')
                return "//www.gravatar.com/avatar/" + hash + "?d=identicon&s=50"; 
            if (icon_set == 'unicorn')
                return "//unicornify.appspot.com/avatar/" + hash + "?s=50";
            if (icon_set == 'wavatar')
                return "//www.gravatar.com/avatar/" + hash + "?d=wavatar&s=50";
            if (icon_set == 'monster')
                return "//www.gravatar.com/avatar/" + hash + "?d=monsterid&s=50";
            if (icon_set == 'retro')
                return "//www.gravatar.com/avatar/" + hash + "?d=retro&s=50";
            if (icon_set == 'robot')
                return "//robohash.org/" + hash + "?size=50x50";
            return null;
        },
        render: function() {
            var icon_set = profile.get('settings')['icon_set'];
            return React.DOM.img({src: this.getSrc(this.props.hash, icon_set)});
        }
    });

    return Icon;

});
