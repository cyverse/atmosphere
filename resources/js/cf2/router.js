/* Router: maps hash navigation */

Atmo.Router = Backbone.Router.extend({
    routes: {
        "": "instances",
        "instances": "instances",
        "instances/:instance_id": "select_instance",
        "volumes": "volumes",
        "volumes/:volume_id": "select_volume",
        "new_instance": "new_instance",
        "new_instance/:image_query": "select_image",
        "settings": "settings"
    },
    initialize: function() {
      Atmo.profile = new Atmo.Models.Profile();
      Atmo.profile.fetch({
        async: false,
        success: function(profile, foo, bar) {
          $("#username").html(profile.get('id'));
        }, 
        error: function() {
          window.location.replace(site_root+"/CASlogin/"+site_root+"/login/");
        }
      });
      Atmo.Utils.update_weather();
      Atmo.providers = new Atmo.Collections.Providers();
      Atmo.providers.fetch({
        async: false,
        success: function(providers, foo, bar) {
        }
      });

      var identity = Atmo.profile.get('selected_identity');
      Atmo.instances = new Atmo.Collections.Instances();
      Atmo.volumes = new Atmo.Collections.Volumes();
      Atmo.images = new Atmo.Collections.Machines();
      Atmo.instance_types = new Atmo.Collections.Sizes();
      Atmo.notifications = new Atmo.Collections.Notifications();
      
      new Atmo.Views.Sidebar({el: $('#menu_wrapper')}).render();
      
      Atmo.instance_types.fetch({async: false});
      Atmo.instances.fetch({
        async: false,
        success: function(collection) {
          collection.test_shell_vnc();
        }
      });
      Atmo.volumes.fetch();
      Atmo.images.fetch();

      this.main = new Atmo.Views.Main({el: $('#main')[0]}).render();

        setInterval(function() {
            $('#refresh_instances_button').click();
        }, 5*60*1000);

        new Atmo.Views.FeedbackLink({el: $('#feedback_link')[0]});
		Atmo.request_resources_modal = new Atmo.Views.RequestResourcesModal();
		$('body').append(Atmo.request_resources_modal.render().el);

        Atmo.alert_modal = new Atmo.Views.AlertModal();
        $('body').append(Atmo.alert_modal.render().el);

		// Populate the top menu with a provider switcher 
        $.ajax({
            type: 'GET',
            url: site_root + '/api/group/', 
            success: function(response_text) {
				identities = response_text[0].identities;

                // Create a summary for each view and identity
                for (var i = 0; i < identities.length; i++) {

					$('#providers_menu').append($('<li>', {
						html: function() {

							var name = _.filter(Atmo.providers.models, function(provider) {
								return provider.get('id') == identities[i].provider_id;	
							});

							if (Atmo.profile.get('selected_identity').get('id') == identities[i].id)
								return '<a href="#" class="current-provider"><i class="icon-ok"></i> ' + name[0].attributes.type + '</a>';
							else 
								return '<a data-provider-id="' + identities[i].provider_id + '" data-identity-id="' + identities[i].id + '">' + name[0].attributes.type + '</a>';
						},
						click: function(e) {
							e.preventDefault();

							var id = parseInt($(this).find('a').attr('data-identity-id'));

							if (Atmo.profile.get('selected_identity').get('id') != id) {
								Atmo.profile.save(
									{ 'selected_identity' : id },
									{ async : false, 
									patch: true, 
									success: location.reload() }
								);	
							}
							else {
								return false;
							}
						}
					}));
                }
            },
			error: function() {
				Atmo.Utils.notify("Could not load all cloud identities", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
			},
            dataType: 'json'
        });

        $('#contact_support').click(function(e) {
            e.preventDefault();
            $('#feedback_link').trigger('click');
        });
        $('#beta_tester_link').click(function(e) {
            e.preventDefault();
            var header = 'A new cloud is coming!';
            var body = 'Atmosphere will soon host OpenStack cloud.<br /><br />';
            body += 'We need beta testers who can help us by reporting the problems and errors they experience.<br /><br />';
            body += 'If you would like to try the OpenStack cloud integration early, please click the "Notify me when it\'s ready" button and we will send you an email when the beta program is available in early January.';
            Atmo.Utils.confirm(header, body, { 
                on_confirm: function() { 
                    var data = {};
                    data["username"] = Atmo.profile.get('id');
                    data["message"] = data["username"] + ' wants to beta test OpenStack.\n';
                    data["subject"] = 'Atmosphere User ' + data["username"] + ' wants to beta test OpenStack';
					// Create a list of user's instances and volumes to make support easier
					data["message"] += '\n\n' + Atmo.profile.get('id') + "'s Instances:";
					for (var i = 0; i < Atmo.instances.length; i++) {
						var instance = Atmo.instances.models[i];
						data["message"] += '\nID:\t\t' + instance.get('id') + '\nEMI:\t\t' + instance.get('image_id') + '\nIP:\t\t' + instance.get('public_dns_name');
					}
					data["message"] += '\n\n' + Atmo.profile.get('id') + "'s Volumes:";
					for (var i = 0; i < Atmo.volumes.length; i++) {
						var volume = Atmo.volumes.models[i];
						data["message"] += '\nID:\t\t' + volume.get('id') + '\nName:\t\t' + volume.get('name');
					}
					data["message"] += '\n\n';

					data['location'] = window.location.href,
					data['resolution'] = { 
						'viewport': {
							'width': $(window).width(),
							'height': $(window).height()
						},
						'screen': {
							'width':  screen.width,
							'height': screen.height
						}
					};

                    $.ajax({
                        type: 'POST',
                        url: site_root + '/api/email_support/', 
                        data: data,
                        statusCode: {
                            200:  function() {
                                Atmo.Utils.notify("Thank you!", "We will email you when the OpenStack cloud is ready for testing.");
                            }
                        },
                        contentType: 'json',
                        dataType: 'json'
                    });
                }, 
                ok_button: 'Notify me when it\'s ready'
            });
        });


        new Atmo.Views.NotificationHolder({el: $('#alert_holder')[0]});
    },
    instances: function() {
        this.main.show_instance_screen();

        if (Atmo.instances.models.length > 0 && !Atmo.instances.selected_instance) {
            Atmo.instances.select_instance(Atmo.instances.models[0]);
        }
		else {
			Backbone.history.navigate('instances');
		}

        // Hide all help tips so none remain after navigating away from it
        Atmo.Utils.hide_all_help();
    },
    volumes: function() {
        this.main.show_volume_screen();
        // Hide all help tips so none remain after navigating away from it
        Atmo.Utils.hide_all_help();
    },
    new_instance: function(options) {
        this.main.show_new_instance_screen();
        // Hide all help tips so none remain after navigating away from it
        Atmo.Utils.hide_all_help();
    },
    settings: function() {
        this.main.show_settings_screen();
    },
    select_instance: function(instance_id) {
        this.instances();
        var instance;
        if (instance = Atmo.instances.get(instance_id))
            Atmo.instances.select_instance(instance);
    },
    select_volume: function(volume_id) {
        var volume = Atmo.volumes.get(volume_id);
        if (volume)
            Atmo.volumes.select_volume(volume);
        //console.log(volume_id);
    },
    select_image: function(image_query) {
        if (this.new_instance_screen)
            this.new_instance_screen.set_query(image_query);
        else
            this.new_instance({'query': image_query});
    }
});

$(document).ready(function() {
  window.app = new Atmo.Router();
  Backbone.history.start();
});
