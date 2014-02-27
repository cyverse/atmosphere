Atmo.Views.SettingsScreenIdentitySummary = Backbone.View.extend({
  template: _.template(Atmo.Templates['identity_summary']),
  tagName: 'div',
  className: "panel panel-default",
  attributes: {'data-populated' : 'false'},
  initialize: function() {
    
    // Will need to bind: if user changed info about an identity, this.rerender_provider_data.
    
    this.provider = this.options.provider;
    this.identity_id = this.options.identity_id;
    
    Atmo.profile.bind("change", this.render, this);
    Atmo.profile.bind('fail', this.fail_profile, this);
    if (Atmo.instances) {
      Atmo.instances.bind("add", this.rerender_provider_data, this);
      Atmo.instances.bind("remove", this.rerender_provider_data, this);
      Atmo.instances.bind("change", this.rerender_provider_data, this);
      Atmo.instances.bind('fail', this.fail_instances, this);
    }
    if (Atmo.volumes) {
      Atmo.volumes.bind("change", this.rerender_provider_data, this);
      Atmo.volumes.bind("add", this.rerender_provider_data, this);
      Atmo.volumes.bind("remove", this.rerender_provider_data, this);
      Atmo.volumes.bind('fail', this.fail_volumes, this);
    }
    this.maintenance = Atmo.maintenances.in_maintenance(this.provider);

    this.rendered = false;
  },
  events: {
    'click a.accordion-toggle' : 'render_provider_data',
    //'click #help_edit_login_key' : 'edit_login_key',
  },
  is_populated: function() {
    return this.$el.attr('data-populated') == "true";
  },
  set_populated: function(populated) {
    this.$el.attr('data-populated', populated);
  },
  toggle_collapse: function() {
    //this.$el.find('.panel-body').collapse('toggle');
    this.$el.find('.panel-collapse').collapse('toggle');
  },
  render: function() {
    if (Atmo.profile.isNew() || this.rendered)
      return this;
    
    var self = this;
    
    var identity = { id: self.identity_id, provider: self.provider };
    var identity_provider_id = identity.provider;
    var in_maintenance = Atmo.maintenances.in_maintenance(identity_provider_id);
    var name = _.filter(Atmo.providers.models, function(provider) {
      return provider.get('id') == self.provider;    
    });
    identity.provider_name = name[0].attributes.location;
    this.$el.html(this.template(identity));
    if (Atmo.profile.get('selected_identity').id == self.identity_id) {
      if(in_maintenance) {
this.$el.find('a.accordion-toggle').html(identity.provider_name + ' <span class="label" style="background-color: #0098aa">CURRENT</span><i class="maint-icon glphicon glphicon-warning-sign"></i>maintenance');
this.$el.find('.control_radio').attr('checked', 'checked');
} else {
this.$el.find('a.accordion-toggle').html(identity.provider_name + ' <span class="label" style="background-color: #0098aa">CURRENT</span>');
this.$el.find('.control_radio').attr('checked', 'checked');                        
}
} else {
if(in_maintenance) {
this.$el.find('a.accordion-toggle').html(identity.provider_name + ' <i class="maint-icon glphicon glphicon-warning-sign"></i>maintenance');
}
}

// Point controls to this provider
this.$el.find('#identity_num').attr('id', 'identity_'+self.identity_id);
this.$el.find('a[href="#identity_num"]').attr('href', 'identity_'+self.identity_id);

this.rendered = true;

return this;
},
/*edit_login_key: function(e) {
    e.preventDefault();

    var header = 'Edit Cloud Identity';
    var content = '<form name="update_identity">';
    content += '<label for="login">Username</label>';
    content += '<input type="text" name="login" disabled="disabled" placeholder="'+Atmo.profile.get('id')+'"><br />';
    content += '<label for="key">Password</label>';
    content += '<span class="help-block"><a href="https://user.iplantcollaborative.org/reset/request">Reset Your Password</a></span>';
    content += '<label for="alias">New Alias</label>';
    content += '<input type="text" name="alias" value="' + Atmo.profile.get('id') + '" />';
    content += '</form>';

    Atmo.Utils.confirm(header, content, { on_confirm: function() {
	// Update stuff
    }, 
	ok_button: 'Update Identity'
    });

},*/
rerender_provider_data: function() {
this.set_populated(false);
},
render_provider_data: function(e) {
// Do some mapping, based on whether the info we want to see already exists in backbone models
// This should be majorly refactored when we have time
if (!this.maintenance) {
if (Atmo.profile.get('selected_identity').id == this.identity_id) {
this.render_local_summary(e);
} else {
this.render_remote_summary(e);
}
}
},
render_remote_summary: function(e) {
var self = this;
if (!this.is_populated()) {
// Help the user -- hide everything that's being appended until we get to the end. Meantime, show a spinny loader!
// Keep track of any errors
var errors = Array();
self.$el.find('.accordion-inner').children().hide();

var loader = $('<div>', {
html: '<img src="'+site_root+'/resources/images/loader_large.gif" />',
style: 'display: none; text-align: center;'
});
self.$el.find('.accordion-inner').prepend(loader);

      $(e.target).parent().parent().find('.accordion-body').collapse('toggle');
      loader.slideDown(400, function() {
        
    // Display the provider's resource charts
    self.cpu_resource_chart = new Atmo.Views.ResourceCharts({
      el: self.$el.find('#cpuHolder'),
      quota_type: 'cpu',
      provider_id: self.provider,
      identity_id: self.identity_id
    }).render();
    self.mem_resource_chart = new Atmo.Views.ResourceCharts({
      el: self.$el.find('#memHolder'),
      quota_type: 'mem',
      provider_id: self.provider,
      identity_id: self.identity_id
    }).render();
    self.time_resource_chart = new Atmo.Views.ResourceCharts({
      el: self.$el.find('#allocationHolder'),
      quota_type: 'allocation',
      provider_id: self.provider,
      identity_id: self.identity_id
    }).render();
        
    // Get instances and volumes of this provider and identity 
    $.ajax({
      type: 'GET',
      url: site_root + '/api/v1/provider/' + self.provider + '/identity/' + self.identity_id + '/instance/', 
      success: function(response_text) {
        self.instances = response_text;
            
        // Show all instances associated with this identity
        if (self.instances && self.instances.length > 0) {

          var table = $('<table>', {
        class: 'table table-bordered'
          });
              
          table.append($('<thead>', {
        html: function() {
          var content = '<tr><td width="60%"><strong>Instance Name</strong></td>';
                                    content += '<td width="15%"><strong>Size</strong></td>';
          content += '<td width="25%"><strong>IP Address</strong></td></tr>';
          return content;
        }
          }));
          var tbody = $('<tbody>');
          for (var i = 0; i < self.instances.length; i++) {
        tbody.append($('<tr>', {
          html: function() {
                    
            // Can we get an image URL here?
            //var img = '<img src="' + this.instances.models[i].get('image_url') + '" height="20" width="20" style="border: 1px solid #CCC"> ';
            
            var inst_name = self.instances[i]["name"];
            var content = '<td>'+ inst_name + '</td>';
            content += '<td>' + self.instances[i]['size_alias'] + '</td>';
            content += '<td>' + self.instances[i]['ip_address'] + '</td>';
                    
            return content;
          }
        }));
          }
                            table.append(tbody);
          self.$el.find('#instances_'+self.identity_id).html(table);
              
        }
      },
      error: function() {
        errors.push("Could not load instances for this cloud identity.");
        self.fail_instances();
      },
      dataType: 'json'
    });
        
    self.disk_count_resource_chart = new Atmo.Views.ResourceCharts({
      el: self.$el.find('#disk_countHolder'),
      quota_type: 'disk_count',
      identity_id: self.identity_id,
      provider_id: self.provider
    }).render();
        
    self.disk_resource_chart = new Atmo.Views.ResourceCharts({
      el: self.$el.find('#diskHolder'),
      quota_type: 'disk',
      identity_id: self.identity_id,
      provider_id: self.provider
    }).render();
    
    $.ajax({
      type: 'GET',
      url: site_root + '/api/v1/provider/' + self.provider + '/identity/' + self.identity_id + '/volume/', 
      success: function(response_text) {
        self.volumes = response_text;
            
        if (self.volumes && self.volumes.length > 0) {
          var vol_table = $('<table>', {
        class: 'table table-bordered'
          });
              
          vol_table.append($('<thead>', {
        html: function() {
          var content = '<tr><td width="60%"><strong>Volume Name</strong></td>';
          content += '<td width="15%"><strong>Capacity</strong></td>';
          content += '<td width="25%"><strong>Status</strong></td></tr>';
          return content;
        }
          }));
          var vol_tbody = $('<tbody>');
          for (var i = 0; i < self.volumes.length; i++) {
        vol_tbody.append($('<tr>', {
          html: function() {
                    
            var img = '<img src="' + site_root + '/resources/images/mini_vol.png"> ';
            var name = (self.volumes[i]['name'] || self.volumes[i]['id']);
            var content = '<td>' + img + name + '</td>';
            content += '<td>' + self.volumes[i]['size'] + ' GB</td>';
            content += '<td>';
            if (self.volumes[i]['status'] == 'in-use') {
              content += 'Attached';
            }
            else {
              content += 'Available';
            }
            content += '</td>';
            return content;
          }
        }));
          }
          vol_table.append(vol_tbody);
          self.$el.find('#volumes_'+self.identity_id).html(vol_table);
        }
        // FINALLY: Data-populated is true, show accordion body
        self.set_populated(true);
            
        setTimeout(function() { 
          loader.remove();
              
          var children = self.$el.find('.accordion-inner .row-fluid');
          children.slideDown();
              
        }, 3000);
      },
      error: function() {
        errors.push("Could not load volumes for this cloud identity.");
        self.fail_volumes();
            
        self.set_populated(true);
            
        setTimeout(function() { 
          loader.remove();
              
          var children = self.$el.find('.accordion-inner .row-fluid');
          children.slideDown();
              
        }, 3000);
      },
      dataType: 'json'
                });
    self.set_populated(true);
      });
    }
    else {
      $(e.target).parent().parent().find('.accordion-body').collapse('toggle');
    }
  },
  render_local_summary: function(e) {
    var self = this;

    if (!self.is_populated()) {
      var loader = $('<div>', {
        html: '<img src="'+site_root+'/resources/images/loader_large.gif" />',
        style: 'display: none; text-align: center;'
      })
        .prependTo(this.$el.find('.panel-body'))
        .slideDown(400, function() {
          
          // Display the provider's resource charts
          self.cpu_resource_chart = new Atmo.Views.ResourceCharts({
            el: self.$el.find('#cpuHolder'),
            quota_type: 'cpu',
          }).render();
          self.mem_resource_chart = new Atmo.Views.ResourceCharts({
            el: self.$el.find('#memHolder'),
            quota_type: 'mem',
          }).render();
          self.disk_count_resource_chart = new Atmo.Views.ResourceCharts({
            el: self.$el.find('#disk_countHolder'),
            quota_type: 'disk_count',
          }).render();
          self.disk_resource_chart = new Atmo.Views.ResourceCharts({
            el: self.$el.find('#diskHolder'),
            quota_type: 'disk',
          }).render();
          
          var identity = Atmo.identities.get(self.identity_id);
          if (identity.has_allocation()) {
            self.time_resource_chart = new Atmo.Views.ResourceCharts({
              el: self.$el.find('#allocationHolder'),
              quota_type: 'allocation',
            }).render();
          } 
          
          // Show all instances associated with this identity
          if (Atmo.instances.length > 0) {
            
            var table = $('<table>', {
              class: 'table table-bordered'
            });
            
            table.append($('<thead>', {
              html: function() {
                var content = '<tr><td width="60%"><strong>Instance Name</strong></td>';
                content += '<td width="15%"><strong>Size</strong></td>';
                content += '<td width="25%"><strong>IP Address</strong></td></tr>';
                return content;
              }
            }));
            var tbody = $('<tbody>');
            for (var i = 0; i < Atmo.instances.length; i++) {
              tbody.append($('<tr>', {
                html: function() {
                  var inst_name = Atmo.instances.models[i].get('name');
                  var content = '<td>'+ inst_name + '</td>';
                  content += '<td>' + Atmo.instances.models[i].get('size_alias') + '</td>';
                  content += '<td>' + Atmo.instances.models[i].get('ip_address') + '</td>';
                  
                  return content;
                }
              }));
            }
            table.append(tbody);
            self.$el.find('#instances_'+self.identity_id).html(table);
            
          }
          
          if (Atmo.volumes.length > 0) {
            var vol_table = $('<table>', {
              class: 'table table-bordered'
            });
            
            vol_table.append($('<thead>', {
              html: function() {
                var content = '<tr><td width="60%"><strong>Volume Name</strong></td>';
                content += '<td width="15%"><strong>Capacity</strong></td>';
                content += '<td width="25%"><strong>Status</strong></td></tr>';
                return content;
              }
            }));

            var vol_tbody = $('<tbody>');
            for (var i = 0; i < Atmo.volumes.length; i++) {
              vol_tbody.append($('<tr>', {
                html: function() {
                  var img = '<img src="' + site_root + '/resources/images/mini_vol.png"> ';
                  var name = (Atmo.volumes.models[i].get('name') || Atmo.volumes.models[i].get('id'));
                  var content = '<td>' + img + name + '</td>';
                  content += '<td>' + Atmo.volumes.models[i].get('size') + ' GB</td>';
                  content += '<td>';
                  if (Atmo.volumes.models[i].get('status') == 'in-use') {
                    content += 'Attached';
                  }
                  else {
                    content += 'Available';
                  }
                  content += '</td>';
                  return content;
                }
              }));
            }
            vol_table.append(vol_tbody);
            self.$el.find('#volumes_'+self.identity_id).html(vol_table);
          }

          // End loader slidedown function
          $(this).remove();
          self.set_populated(true);
        });

    }
    this.toggle_collapse();
  },
  fail_profile: function() {
    //console.log("profile fail");
  },
  fail_instances: function() {
    //console.log("instance fail");
    this.$el.find('#instances_'+this.identity_id).html('Could not load instances for this identity.');
  },
  fail_volumes: function() {
    //console.log("volume fail");
    this.$el.find('#volumes_'+this.identity_id).html('Could not load volumes for this identity.');
  }
});
