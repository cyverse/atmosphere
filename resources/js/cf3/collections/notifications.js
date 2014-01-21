/* notifications.js
 * Backbone.js notification collection.
 */
define(['collections/base', 'models/notification'], function(Base, Notification) {
    return Base.extend({
        model: Notification,
    });
});
