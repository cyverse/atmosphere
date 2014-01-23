define(['react', 'providers'], function(React, providers) {

    var IdentitySelect = React.createClass({
        getInitialState: function() {
            return {};
        },
        onSelect: function(identity_id) {
            this.props.onSelect(this.props.identities.get(identity_id));
        },
        render: function() {
            return React.DOM.ul({
                    className: 'nav nav-tabs identity-select',
                    onChange: this.onSelect
                },
                this.props.identities.map(function(identity) {
                    var provider = providers.get(identity.get('provider_id'));
                    if (!provider)
                        console.error("Unknown provider in identity", identity);
                    return React.DOM.li({className: this.props.selected == identity ? "active" : ""},
                        React.DOM.a({
                                href: '#',
                                onClick: function(e) {
                                    e.preventDefault();
                                    this.onSelect(identity.id);
                                }.bind(this)
                            },
                            provider.get('location')));
                }.bind(this))
            );
        }
    });

    return IdentitySelect;

});
