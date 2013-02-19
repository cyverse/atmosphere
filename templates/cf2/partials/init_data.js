{% autoescape off %}
(function() {

    var user_profile = {{ user_profile }};
    var instance_list = {{ instance_list }};
    var volume_list = {{ volume_list }};

    var store_if_valid = function(result, key) {
        if (!result || !result['result'] || !result['result']['code'] || result['result']['code'] != 'success')
            return;
        sessionStorage.setItem(key, JSON.stringify(result['result']['value']));
    };

    store_if_valid(user_profile, '__getUserProfile');
    store_if_valid(instance_list, '__getInstanceList');
    store_if_valid(volume_list, '__getVolumeList');

})();
{% endautoescape %}
