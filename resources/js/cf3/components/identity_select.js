define(['react'], function(React) {

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
                    return React.DOM.option({
                        'value': identity.id
                    }, "Provider " + identity.get('provider_id') + ", Identity " + identity.id);
                })
            );
        }
    });

    return IdentitySelect;

});
