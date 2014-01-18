define(['react'], function(React) {

var Utils = {};

Utils.seconds_to_pretty_time = function(seconds, precision) {
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

Utils.relative_time = function(date_obj) {
    var now = new Date();
    var seconds = Math.floor((new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), now.getMinutes(), now.getSeconds()) - date_obj) / 1000);

    var time = Utils.seconds_to_pretty_time(seconds, 1);

    return time + ' ago';
};

return Utils;

});
