define(['react', 'components/header', 'components/sidebar', 'components/footer', 'components/dashboard'], function (React, Header, Sidebar, Footer, Dashboard) {
    var sidebar_items = [
        ['Dashboard', 'home'],
        ['App Store', 'shopping-cart'],
        ['Instances', 'cloud-download'],
        ['Volumes', 'hdd'],
        ['Images', 'camera'],
        ['Cloud Providers', 'cloud'],
        ['Quotas', 'tasks'],
        ['Settings', 'cog'],
        ['Help', 'question-sign']
    ];

    var Application = React.createClass({
        getInitialState: function() {
            return {active: 'Dashboard'};
        },
        render: function() {
            return React.DOM.div({},
                Header(),
                Sidebar({items: sidebar_items, active: this.state.active}),
                React.DOM.div({'id': 'main'}, Dashboard()),
                Footer()
            );
        }
    });

    return Application;
});
