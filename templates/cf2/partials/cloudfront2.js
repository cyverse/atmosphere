
/* load templates */
{% for name, text in templates.items %}
Atmo.Templates["{{ name }}"] = "{{ text|escapejs }}";
{% endfor %}
/* end templates */
