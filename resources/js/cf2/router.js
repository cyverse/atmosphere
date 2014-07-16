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
	  Atmo.identities = new Atmo.Collections.Identities();
	  Atmo.identities.fetch({
		  async: false,
	  });

      var identity = Atmo.profile.get('selected_identity');
      var identity_provider_id = identity.get("provider_id");

      Atmo.maintenances = new Atmo.Collections.Maintenances();
      Atmo.maintenances.fetch({
        async: false,
      });
        Atmo.instances = new Atmo.Collections.Instances();
        Atmo.volumes = new Atmo.Collections.Volumes();
        Atmo.images = new Atmo.Collections.Machines();
        if (Atmo.profile.get('is_staff') === true) {
            Atmo.instance_hypervisors = new Atmo.Collections.Hypervisors();
            Atmo.instance_hypervisors.fetch({async: false});
        }
        Atmo.instance_types = new Atmo.Collections.Sizes();

      Atmo.notifications = new Atmo.Collections.Notifications();
      
      this.main = new Atmo.Views.Main({el: $('#main')[0]}).render();
      new Atmo.Views.Sidebar({el: $('#menu_wrapper')}).render();


      setInterval(function() {
        $('#refresh_instances_button').click();
      }, 5*60*1000);

      new Atmo.Views.FeedbackLink({el: $('#feedback_link')[0]});
      Atmo.request_resources_modal = new Atmo.Views.RequestResourcesModal();
      $('body').append(Atmo.request_resources_modal.render().el);

      Atmo.alert_modal = new Atmo.Views.AlertModal();
      $('body').append(Atmo.alert_modal.render().el);

      // Populate the top menu with a provider switcher 
      for (var i = 0; i < Atmo.identities.length; i++) {
	var identity = Atmo.identities.models[i];
        var identity_provider_id = identity.get('provider_id');
        var in_maintenance = Atmo.maintenances.in_maintenance(identity_provider_id);
        var result = '';
	var name = Atmo.identities.models[i].get('provider').get('location');
	$('#providers_menu').append($('<li>', {
	  html: function() {
	    if (identity.get('selected')){
	      result = '<a href="#" class="current-provider"><i class="glyphicon glyphicon-ok"></i> ' + name;
            } else {
              result = '<a href="#">' + name;
            }
            if (in_maintenance) {
              result += ' <i class="glyphicon glyphicon-warning-sign maint-icon"></i>';
            }
            result += '</a>';
            return result;
	  },
	  click: function(e) {
	    e.preventDefault();
	    var identity = $(this).data();
            if (in_maintenance) {
              Atmo.Utils.notify('Error', identity.get('provider').get('type') + ' is currently in maintenance.');
	      return false;
            }
	    if (identity.get('selected')) {
	      Atmo.Utils.notify('Error', 'You are already using ' + identity.get('provider').get('type') + ' as your provider.');
	      return false;
	    }
	    else {
	      Atmo.profile.save({'selected_identity': identity.get('id')},
				{'async': false,
				 'patch' : true,
				 success: location.reload()});
	    }
          }
        }).data(identity));
      }
      
      $('#contact_support').click(function(e) {
        e.preventDefault();
        $('#feedback_link').trigger('click');
                                  });
        $.ajax({
                   type: 'GET',
                   url: site_root + '/api/v1/version/',
                   statusCode: {
                       200:  function(response) {
                           $('#version').html('<a href="https://github.com/iPlantCollaborativeOpenSource/atmosphere/tree/'
                                              + response['git_sha'] + '">'
                                              + new Date(response['date']).toString("F") + ' '
                                              + '(' + response['git_sha_abbrev'] + ')</a>');
                       }
                   },
               });
      $('#total_cpu_time a').click(function() {
	$('#cpu_modal').modal('show');
      });
      new Atmo.Views.NotificationHolder({el: $('#alert_holder')[0]});
    },
  instances: function() {
    var identity = Atmo.profile.get('selected_identity');
    var identity_provider_id = identity.get("provider_id");
    if(!Atmo.maintenances.in_maintenance(identity_provider_id)){
      this.main.show_instance_screen();
      Atmo.instances.on('reset', function(collection) {
           if (!collection.isEmpty() && !collection.selected_instance)
               collection.select_instance(collection.at(0));
      });
        // Hide all help tips so none remain after navigating away from it
        Atmo.Utils.hide_all_help();
      }
    },
    volumes: function() {
      var identity = Atmo.profile.get('selected_identity');
      var identity_provider_id = identity.get("provider_id");
      if(!Atmo.maintenances.in_maintenance(identity_provider_id)){
        this.main.show_volume_screen();
        // Hide all help tips so none remain after navigating away from it
        Atmo.Utils.hide_all_help();
      }
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

  var identity = Atmo.profile.get('selected_identity');
  var identity_provider_id = identity.get("provider_id");
  if (!Atmo.maintenances.in_maintenance(identity_provider_id)) {
        Atmo.instance_types.fetch({async: false});
        Atmo.instances.fetch();
        Atmo.volumes.fetch();
        Atmo.images.fetch();
  }
});
