define(['models/base'], function(Base) {
    return Base.extend({
        defaults: {
            'header': null,
            'body': null,
            'timestamp': null,
            'sticky': false,
            'type': 'info' // one of success, info, warning, danger
        }
    });
});
