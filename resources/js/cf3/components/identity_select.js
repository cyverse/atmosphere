define(['react', 'providers'], function(React, providers) {

    var IdentitySelect = React.createClass({
        getInitialState: function() {
            return {};
        },
        onSelect: function(e) {
            var identity_id = e.target.value;
            this.props.onSelect(this.props.identities.get(identity_id));
        },
        render: function() {
            return React.DOM.select({
                    onChange: this.onSelect
                },
                this.props.identities.map(function(identity) {
                    var provider = providers.get(identity.get('provider_id'));
                    if (!provider)
                        console.error("Unknown provider in identity", identity);
                    return React.DOM.option({'value': identity.id}, 
                        provider.get('location') 
                    )
                })
            );
        }
    });

    return IdentitySelect;

});
