Atmo.Collections.Maintenances = Atmo.Collections.Base.extend({
  model: Atmo.Models.Maintenance,
  url: function(){
    return url = this.urlRoot
      + '/' + this.model.prototype.defaults.model_name + '/?active=True';
  },
  in_maintenance: function(provider_id){
    var result = false;
    if (!(Atmo.profile.get('is_staff') || Atmo.profile.get('is_superuser'))) {
      if (this.length > 0) {
        this.each(function(m) {
          var m_provider_id = m.get("provider_id");
          if ( m.get('disable') ||
                  (m_provider_id == null || m_provider_id == provider_id)) {
              result = true;
          }
        });
      }
    }
    return result;
  }
});
