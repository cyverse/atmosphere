Atmo.Views.Main = Backbone.View.extend({
    initialize: function() {

    },
    render: function() {
      var identity_provider_id = Atmo.profile.get('selected_identity').get('provider_id');
      if(!Atmo.maintenances.in_maintenance(identity_provider_id)) {
        Atmo.instances.bind('select', this.show_instance_screen);
        this.instance_screen  = new Atmo.Views.InstanceScreen();
        this.$el.append(this.instance_screen.render().el);

        this.volume_screen  = new Atmo.Views.VolumeScreen();
        this.$el.append(this.volume_screen.render().el);
        this.volume_screen.$el.hide();

        this.settings_screen  = new Atmo.Views.SettingsScreen();
        this.$el.append(this.settings_screen.render().el);
      } else {
        this.instance_screen  = new Atmo.Views.InstanceScreen();
        this.$el.append(this.instance_screen.render().el);

        this.settings_screen  = new Atmo.Views.SettingsScreen();
        this.$el.append(this.settings_screen.render().el);
        this.settings_screen.$el.hide();
      }
	  //Logging out of CAS!!!!!
	  $('#logout_button').click(function(){
		  var header = "Logging Out of Atmosphere";
		  var body = "You will be logged out of Atmosphere in <span id='countdown_time'></span> seconds.<br\><br\>Would you like to log out of all iPlant applications?";

		  new Atmo.Views.AlertModal().render().do_alert(header,body,{
				ok_button: "Log out of all iPlant services",
				on_confirm: function(){
					var csrftoken = Atmo.Utils.getCookie('csrftoken');
					Atmo.Utils.post_to_url(site_root + "/logout/", { cas: true, 'csrfmiddlewaretoken':csrftoken })
				},

				cancel_button: "Log out of Atmosphere Only",
		  		on_cancel: function(){
					window.location.replace(site_root + "/logout/");	
				}
		  });

		  var count = 10;
		  var timeout;
		  (timeout = function() {
			$("#countdown_time").html(count);
			count--;
			if (count > 0)
				window.setTimeout(timeout, 1000);
			else 
				window.location.replace(site_root + "/logout/");	
		  })();
	  });

      return this;
    },
    show_volume_screen: function() {
        $('#main .screen').hide();
        $('#volumeList').show();

        resizeApp();
    },
    show_instance_screen: function() {
        $('#main .screen').hide();
        $('#instanceList').show();

        resizeApp();
    },
    show_new_instance_screen: function(options) {
        if (!options) options = {};

        $('#main .screen').hide();

        if ($('#imageStore').length) {
            $('#imageStore').show();
        } else {
            this.new_instance_screen  = new Atmo.Views.NewInstanceScreen(options);
            $('#main').append(this.new_instance_screen.render().el);
        }
        resizeApp();
    },
    show_settings_screen: function() {
        $('#main .screen').hide();
        this.settings_screen.$el.show();

        resizeApp();
    }
});
