Atmo.Views.Main = Backbone.View.extend({
    initialize: function() {
	    Atmo.images.bind('select', this.select_image, this);
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
    show_images_screen: function(options) {
        if (!options) options = {};

        $('#main .screen').hide();

        if ($('#imageStore').length) {
            $('#imageStore').show();
        } else {
            this.image_screen  = new Atmo.Views.ImageScreen(options);
            $('#main').append(this.image_screen.render().el);
        }
        resizeApp();
    },
    select_image: function(model) {
        var detail_screen = new Atmo.Views.ImageDetail({model: model});
        $('#main')
            .find('.image-detail').remove().end()
            .find('.screen').hide().end()
            .append(detail_screen.render().el);
        resizeApp();
    },
    show_settings_screen: function() {
        $('#main .screen').hide();
        this.settings_screen.$el.show();

        resizeApp();
    }
});
