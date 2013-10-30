Atmo.Views.Sidebar = Backbone.View.extend({
  'tagName': 'div',
  events: {
    'click #instance_link, #volume_link': 'select_link',
    'click #refresh_instances_button' : 'refresh_instance_list',
  },
  initialize: function() {
    Atmo.instances.bind('fail', this.stop_spinner, this);
    Atmo.instances.bind('change:selected', this.change_selection, this);
    Atmo.volumes.bind('change:selected', this.change_selection, this);
  },
  render: function() {
    this.$el.find('#instance_link_list, #volume_link_list').remove();
    this.$el.find('#instance_link').append('<ul class="link_list" id="instance_link_list">').addClass('active');
    this.$el.find('#volume_link').append('<ul class="link_list" id="volume_link_list">');
    
    new Atmo.Views.SidebarInstanceList({
	    el: this.$el.find('#instance_link_list'), 
      collection: Atmo.instances
    });
    
    new Atmo.Views.SidebarVolumeList({
      el: this.$el.find('#volume_link_list'), 
      collection: Atmo.volumes
    });
    
    var self = this;
    
    // Show users how much money they've saved using Atmosphere
    $.ajax({ 
      url: '/api/leaderboard?username='+Atmo.profile.get('id'),
      type: 'GET',
      statusCode: {
	200: function(data) {
        if(data.length == 0) {
            return;
        }
	  var used = ""+(data[0]["total_cpu_time"] / 3600).toNumberCommaString();
	  var time = Atmo.Utils.seconds_to_pretty_time(data[0]["total_uptime"], 3);
          
	  $('#total_cpu_time strong').html(used);
	}
      }	
    });
    
  },
  select_link: function(e) {
    $(e.currentTarget).siblings().removeClass('active');
    $(e.currentTarget).addClass('active');
  },
  change_selection: function(model) {
    this.$el.find('#instance_link, #volume_link').removeClass('active');
    if (model instanceof Atmo.Models.Instance) {
      this.$el.find('#instance_link').addClass('active');	
      Backbone.history.navigate('#instances', {trigger: true});
    } else if (model instanceof Atmo.Models.Volume) {
      this.$el.find('#volume_link').addClass('active');	
      Backbone.history.navigate('#volumes', {trigger: true});
    } else {
      return false;
    }
  },
  refresh_instance_list: function(e) {
    this.$el.find('#refresh_instances_button img').attr('src', site_root + '/resources/images/loader.gif');
    var self = this;
    
    // Occurs if initial fetch failed
    if (!Atmo.instances.update)
      this.stop_spinner();
    
    Atmo.instances.update({
      success: function() {
	self.$el.find('#refresh_instances_button img').attr('src', site_root + '/resources/images/icon_mini_refresh.png');
      },
      error: function() {
	Atmo.Utils.notify("Could not update instance list", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
	self.$el.find('#refresh_instances_button img').attr('src', site_root + '/resources/images/icon_mini_refresh.png');
	self.stop_spinner();
      },
    });
    
    if (!Atmo.volumes.update)
      this.stop_spinner();
    
    // Occurs if initial fetch failed
    Atmo.volumes.update({
      success: function() {
	self.$el.find('#refresh_instances_button img').attr('src', site_root + '/resources/images/icon_mini_refresh.png');
      },
      error: function() {
	Atmo.Utils.notify("Could not update volume list", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
	self.$el.find('#refresh_instances_button img').attr('src', site_root + '/resources/images/icon_mini_refresh.png');
	self.stop_spinner();
      },
    });
    
    // Also, check for weather updates
    Atmo.Utils.update_weather();
  },
  stop_spinner: function() {
    Atmo.Utils.notify("Could not update instances or volumes.", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
    this.$el.find('#refresh_instances_button img').attr('src', site_root + '/resources/images/icon_mini_refresh.png');
  }
});
