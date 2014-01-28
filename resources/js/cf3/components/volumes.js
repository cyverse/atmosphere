define(['react', 'components/identity_select', 'backbone', 'utils', 
    'components/page_header', 'components/time', 'components/glyphicon',
    'components/button_group', 'components/modal', 'models/volume',
    'underscore', 'profile'],
    function(React, IdentitySelect, Backbone, Utils, PageHeader, Time, 
        Glyphicon, ButtonGroup, Modal, Volume, _, profile) {

    var VolumeListItem = React.createClass({
        render: function() {
            var attach_info = [];
            if (this.props.volume.get('status') == 'attaching')
                attach_info = "Attaching";
            else if (this.props.volume.get('status') == 'detaching')
                attach_info = "Detaching";
            else if (this.props.volume.get('status') == 'in-use')
                attach_info = [
                    "Device location: ",
                    React.DOM.code({}, this.props.volume.get('attach_data').device),
                    React.DOM.br(),
                    "Attached: ",
                    Time({date: this.props.volume.get('attach_data').attachTime})
                ];


            return React.DOM.li({},
                Glyphicon({name: 'hdd'}),
                React.DOM.div({className: 'volume-header clearfix'}, 
                    React.DOM.strong({}, 
                        this.props.volume.get('name_or_id')
                    ),
                    " (" + this.props.volume.get('size') + " GB)",
                    ButtonGroup({text: 'Actions', actions: {
                        'Detach': null,
                        'Attach': null,
                        'Report as Broken': null,
                    }})
                ),
                "Created: ",
                Time({date: this.props.volume.get('create_time')}),
                React.DOM.br(),
                attach_info
            );
        }
    });

    var VolumeList = React.createClass({
        render: function() {
            console.log(this.props.volumes);
            var list_items = this.props.volumes.map(function(volume) {
                return VolumeListItem({volume: volume})
            });

            if (list_items.length)
                return React.DOM.ul({id: 'volume-list'}, list_items);
            else
                return React.DOM.div({}, "No volumes");
        }
    });

    var NewVolumeModal = React.createClass({
        getInitialState: function() {
            return {
                volumeName: '',
                volumeSize: '1',
                validSize: true
            }
        },
        handleVolumeNameChange: function(e) {
            this.setState({volumeName: e.target.value});
        },
        handleVolumeSizeChange: function(e) {
            var size = Utils.filterInt(this.state.volumeSize);
            var valid = size && size > 0;

            this.setState({
                volumeSize: e.target.value,
                validSize: valid
            });
        },
        handleSubmit: function(e) {
            e.preventDefault();
            console.log(e);
            console.log(this.state);
            if (!this.state.validSize)
                return;

            /*
             * TODO: Make name not a required field on the API
             */
            var volume = new Volume({}, {identity: this.props.identity});
            console.log(volume);
            var params = {
                name: this.state.volumeName,
                size: this.state.volumeSize
            };
            volume.save(params, {
                wait: true,
                success: function(model) {
                    console.log(model);
                },
                error: function() {
                    console.error('error');
                }
            });
        },
        render: function() {
            return Modal({id: 'volume-create-modal', title: "New Volume"},
                React.DOM.form({role: 'form', onSubmit: this.handleSubmit},
                    React.DOM.div({className: 'modal-body'}, 
                        React.DOM.div({className: 'form-group'},
                            React.DOM.label({htmlFor: 'volume-name'}, "Name"),
                            React.DOM.input({type: 'text', 
                                id: 'volume-name',
                                placeholder: 'My Volume',
                                value: this.state.volumeName,
                                onChange: this.handleVolumeNameChange,
                                className: 'form-control'})),
                        React.DOM.div({
                            className: 'form-group ' + (this.state.validSize ? '' : 'has-error')},
                            React.DOM.label({
                                className: 'control-label', 
                                htmlFor: 'volume-size'},
                                "Capacity (GBs)"),
                            React.DOM.input({type: 'number', 
                                id: 'volume-size',
                                value: this.state.volumeSize,
                                onChange: this.handleVolumeSizeChange,
                                className: 'form-control'}),
                            React.DOM.span({
                                className: 'help-block', 
                                style: {display: this.state.validSize ? 'none': 'block'}}, 
                                "Volume size must be a positive integer"))),
                    React.DOM.div({className: 'modal-footer'}, 
                        React.DOM.button({
                            type: 'submit',
                            className: 'btn btn-primary',
                            disabled: !this.state.validSize},
                            "Create"))));
        }
    });

    var VolumeControls = React.createClass({
        render: function() {
            return React.DOM.div({id: 'volume-controls'},
                React.DOM.button({
                    className: 'btn btn-primary',
                    'data-target': '#volume-create-modal',
                    'data-toggle': 'modal'
                    }, "New Volume"),
                NewVolumeModal({identity: this.props.selected}))
        }
    });

    var Volumes = React.createClass({
        getInitialState: function() {
            return {
                identity: profile.get('identities').at(0)
            };
        },
        setIdentity: function() {
            this.setState({identity: this.state.identity});
        },
        onSelect: function(identity) {
            this.state.identity.get('volumes').off('sync', this.setIdentity);
            identity.get('volumes').on('sync', this.setIdentity);
            this.setState({identity: identity}, function() {
                identity.get('volumes').fetch();
            });
        },
        helpText: function() {
            var links = [
                {href: "https://pods.iplantcollaborative.org/wiki/x/OKxm", text: "Creating a Volume"},
                {href: "https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step3%3AAttachthevolumetotherunninginstance.", text: "Attaching a Volume to an Instance"},
                {href: "https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step5%3ACreatethefilesystem%28onetimeonly%29.", text: "Formatting a Volume"},
                {href: "https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step6%3AMountthefilesystemonthepartition.", text: "Mounting a Volume"},
                {href: "https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step7%3AUnmountanddetachthevolume.", text: "Unmounting and Detaching Volume"},
            ];

            var list_items = _(links).map(function(link) {
                return React.DOM.li({},
                    React.DOM.a({href: link.href, target: '_blank'}, link.text));
            });

            return [
                React.DOM.p({}, 'A volume is like a virtual USB drive that makes it easy to transfer relatively small data between instances.'),
                React.DOM.p({}, 'You can create a volume with a capacity up to 100 GB by clicking the "New Volume" button and completing the form. To store and transfer more data at once, store it in the iPlant Data Store instead. You can mount the Data Store similarly to a volume. (', React.DOM.a({href: 'https://pods.iplantcollaborative.org/wiki/x/S6xm', target: '_blank'}, 'Learn How'), ")"),
                React.DOM.p({}, 'More information about volumes:', React.DOM.ul({}, list_items))
            ];
                
        },
        render: function() {
            return React.DOM.div({style: {display: this.props.visible ? 'block' : 'none'}},
                PageHeader({title: "Volumes", helpText: this.helpText}),
                IdentitySelect({
                    identities: profile.get('identities'), 
                    onSelect: this.onSelect,
                    selected: this.state.identity}),
                VolumeControls({
                    selected: this.state.identity, 
                    identities: profile.get('identities')}),
                VolumeList({volumes: this.state.identity.get('volumes')})
            );
        },
        componentDidMount: function() {
            this.state.identity.get('volumes').on('sync', this.setIdentity);
            this.state.identity.get('volumes').fetch();
        },
        componentWillUnmount: function() {
            this.state.identity.get('volumes').off('sync', this.setIdentity);
        }
    });

    return Volumes;
});
