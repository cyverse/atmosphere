define([], function() {

    var Templates = {};

    {% for name, text in templates.items %}
    Templates["{{ name }}"] = "{{ text|escapejs }}";
    {% endfor %}

    return Templates;

});
