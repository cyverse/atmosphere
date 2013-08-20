/** 
 * Global utilities file.  You can call these from anythwere!
 */

Atmo.Utils.seconds_to_pretty_time = function(seconds, precision) {
    // Precision refers to how many subdivisions of time to return
    var pretty_time = "";
    var units_used = 0;
    var ip_units = 0;
    var interval = 0;
    var p_i;
    var periods = [ 
        {'sec' : 31536000,     'unit' : ' year'},
        {'sec' : 2592000,     'unit' : ' month'},
        {'sec' : 86400,     'unit' : ' day'},
        {'sec' : 3600,         'unit' : ' hour'},
        {'sec' : 60,         'unit' : ' minute'},
        {'sec' : 1,         'unit' : ' second'}];

    if (precision == undefined)
        precision = 1;
        
    if (seconds < 1)
        return '0 seconds';

    for (var i = 0, l = periods.length; i < l; i++) {
        p_i = periods[i];
        interval = Math.floor(seconds / p_i.sec);
        ip_units = interval + p_i.unit;
        if (interval >= 1) {
            units_used++;
            pretty_time += (pretty_time.length > 1) ? ', ' + ip_units : ip_units;
            if (interval > 1) {
                pretty_time += 's';
            }
            seconds = (seconds - (interval * p_i.sec));
            if (precision == units_used || i == l) {
                return pretty_time;
            }
        }
    }
    
};

Atmo.Utils.relative_time = function(date_obj) {
    var now = new Date();
    var seconds = Math.floor((new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), now.getMinutes(), now.getSeconds()) - date_obj) / 1000);

    var time = Atmo.Utils.seconds_to_pretty_time(seconds, 1);

    return time + ' ago';
};

Atmo.Utils.evil_chris_time_parse = function(str_date) {
  if(str_date && (typeof str_date == 'object') && str_date.length > 19) {
    return Date.parse(str_date.substring(0,19)).setTimezoneOffset(0);
  }  
};

Atmo.Utils.hide_all_help = function() {
    $('[id^=help_]').popover('hide');
};

Atmo.Utils.update_weather = function() {

    $.ajax({
        url: '/api/v1/provider/' + Atmo.profile.get('selected_identity').get('provider_id') + '/occupancy/', 
        type: 'GET',
        success: function(response_text) {

            var occupancy = Math.round(((response_text[0]["total"] - response_text[0]["remaining"]) / response_text[0]["total"]) * 100);
            var weather_classes = ['sunny', 'cloudy', 'rainy', 'stormy'];
            var weather = '';

            if(occupancy > 85)
                weather = weather_classes[3]
            else if(occupancy > 60)
                weather = weather_classes[2]
            else if(occupancy > 35)
                weather = weather_classes[1]
            else if(occupancy >= 0)
                weather = weather_classes[0]

            if (!$('#weather_report').hasClass(weather)) {
                $.each(weather_classes, function(k, v) {
                    $('body').removeClass(v);
                });
                $('#weather_report').addClass(weather);

                // Hardcoded for now, replace when we have identities in backbone models
                $('#weather_report').html(function() {
                    var content = (Atmo.profile.get('selected_identity').get('provider_id') == 2) ? 'OpenStack' : 'Eucalyptus';
                    content += ' is at ' + occupancy + '% capacity.<br /> The forecast is '+weather+'.';
                    return content;
                });
            }

        }, 
        error: function() {
            var weather_classes = ['sunny', 'cloudy', 'rainy', 'stormy'];
            weather = 'rainy';
            if (!$('#weather_report').hasClass(weather)) {
                $.each(weather_classes, function(k, v) {
                    $('body').removeClass(v);
                });
                $('#weather_report').addClass(weather);
            }
            $('#weather_report').html('Atmosphere could not determine the capacity and forecast for this cloud.');
        }
    });
};

Atmo.Utils.confirm = function(header, body, options) {
    Atmo.alert_modal.do_alert(header, body, options);
};

Atmo.Utils.notify = function(header, body, options) {
    var defaults = {no_timeout: false};
    var options = options ? _.defaults(options, defaults) : defaults;
    Atmo.notifications.add({'header': header, 'body': body, 'timestamp': new Date(), 'sticky': options.no_timeout });
};

// case-insensitive Levenshtein Distance as defined by http://en.wikipedia.org/wiki/Levenshtein_distance
Atmo.Utils.levenshtein_distance= function(s, t) {
    var len_s = s.length, len_t = t.length, cost = 0;
    s = s.toLowerCase();
    t = t.toLowerCase();

    if (s[0] != t[0])
        cost = 1;

    if (len_s == 0)
        return len_t;
    else if (len_t == 0)
        return len_s;
    else
        return Math.min(
            Atmo.Utils.levenshtein_distance(s.substr(1), t) + 1, 
            Atmo.Utils.levenshtein_distance(s, t.substr(1)) + 1, 
            Atmo.Utils.levenshtein_distance(s.substr(1), t.substr(1)) + cost
        );
}

Atmo.Utils.get_profile = function() {
  profile = new Atmo.Models.Profile();
  var model_name = profile.get('model_name');
  var params = {};
  console.log(params);
  console.log(model_name);
  var url = profile.get('api_url')
    + "/" + model_name;
  console.log(url);
  $.ajax({
    type: "GET",
    contentType:"application/json; charset=utf-8",
    dataType:"json",
    url: url,
    data: params,
    success: function(data, textStatus, jqXHR) {
      console.log(data);
      console.log(textStatus);
      console.log(jqXHR);
      $.each(data, function(key, value) {
        profile.set(key, value);
      });
      console.log("processing in Atmo.Utils.get_profile.success");
      //options.success(profile);
    },
    error: function(data, textStatus, jqXHR) {
      console.log(data);
      console.log(textStatus);
      console.log(jqXHR);
      console.log("processing in Atmo.Utils.get_profile.success");
      //options.error('failed to ' + method
      //              + model_name
      //              + "="
      //              + id);
    },
  });
  return profile;
}

// deprecated.   Use Atmo.profile.get('selected_identity')
Atmo.Utils.current_credentials = function() {
  //console.log("current_credentials");
  return { "provider_id": Atmo.profile.get('selected_identity').get('provider_id'),
           "identity_id": Atmo.profile.get('selected_identity').id
         };
}
Atmo.Utils.attach_volume = function(volume, instance, mount_location, options) {
    var options = options || {};
    console.log("instance to attach to", instance);

    volume.attach_to(instance, mount_location, {
        success: function(response_text) {
            var header = "Volume Successfully Attached";
            var body = 'You must <a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step6%3AMountthefilesystemonthepartition." target="_blank">mount the volume</a> you before you can use it.<br />';
            body += 'If the volume is new, you will need to <a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step5%3ACreatethefilesystem%28onetimeonly%29." target="_blank">create the file system</a> first.';

            console.log("success response text", response_text);

            Atmo.Utils.notify(header, body, { no_timeout: true });
            if (options.success)
                options.success();
        },
        error: function() {
            var header = "Volume attachment failed.";
            var body = "If this problem persists, contact support at <a href=\"mailto:support@iplantcollaborative.org\">support@iplantcollaborative.org</a>"
            Atmo.Utils.notify(header, body, { no_timeout: true});
        }
    });
};

Atmo.Utils.confirm_detach_volume = function(volume, instance, options) {
    var header = "Do you want to detach <strong>"+volume.get('name_or_id')+'</strong>?';
    //TODO: Replace this with a global var Atmo.provider or some such..
    var identity_id = Atmo.profile.get('selected_identity').id;
    var identity = Atmo.identities.get(identity_id);
    var provider_name = identity.get('provider').get('type');
    var body;
    if (provider_name.toLowerCase() === 'openstack') {
        body = '<p class="alert alert-error"><i class="icon-warning-sign"></i> <strong>WARNING</strong> If this volume is mounted, you <u>must</u> stop any running processes that are writing to the mount location before you can detach.</p>'; 
        body += '<p>(<a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step7%3AUnmountanddetachthevolume." target="_blank">Learn more about unmounting and detaching a volume</a>)</p>';
    } else {
        body = '<p class="alert alert-error"><i class="icon-warning-sign"></i> <strong>WARNING</strong> If this volume is mounted, you <u>must</u> unmount it before detaching it.</p>'; 
        body += '<p>If you detach a mounted volume, you run the risk of corrupting your data and the volume itself. (<a href="https://pods.iplantcollaborative.org/wiki/x/OKxm#AttachinganEBSVolumetoanInstance-Step7%3AUnmountanddetachthevolume." target="_blank">Learn more about unmounting and detaching a volume</a>)</p>';
    }

    Atmo.Utils.confirm(header, body, { 
        on_confirm: function() {
            volume.detach(instance, {
                success: function() {
                    Atmo.Utils.notify("Volume Detached", "Volume is now available to attach to another instance or to destroy.");
                    if (options.success)
                        options.success();
                },
                error: function(message, response) {
                    if (provider_name.toLowerCase() === 'openstack') {
                        errors = $.parseJSON(response.responseText).errors
                        var body = '<p class="alert alert-error">' + errors[0].message.replace(/\n/g, '<br />') + '</p>'
                        body += "<p>Please correct the problem and try again. If the problem persists, or you are unsure how to fix the problem, please email <a href=\"mailto:support@iplantcollaborative.org\">support@iplantcollaborative.org</a>.</p>"
                        Atmo.Utils.confirm("Volume failed to detach", body, {
                            //TODO: Remove the 'Cancel' button on this box
                        });
                    } else {
                        Atmo.Utils.notify("Volume failed to detach", "If the problem persists, please email <a href=\"mailto:support@iplantcollaborative.org\">support@iplantcollaborative.org</a>.", {no_timeout: true});
                    }
                }
            }); 
        },
        on_cancel: function() {
            console.log("cancelled volume detach.");
            Atmo.volumes.fetch();
        },
        ok_button: 'Yes, detach this volume'
    });
};

// To show people how much money they've saved by using Atmosphere!

Number.prototype.toCurrencyString = function() {
    return this.toFixed(0).replace(/(\d)(?=(\d{3})+\b)/, '$1,');    
};
