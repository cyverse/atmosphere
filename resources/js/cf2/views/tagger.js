/*
 * Interface that allows for tagging.  Initialize it with a set of default tags,
 * query the set of tags with get_tags().
 * get_tags() returns a list of tags
 * set_editable(boolean editable) to make it editable or not
 */
Atmo.Views.Tagger = Backbone.View.extend({
    template: _.template(Atmo.Templates['tagger']),
    className: 'tagger clearfix',
    events: {
        'click .tag_adder' : 'edit_tags',
        'keyup .new_tag' : 'new_tag_input_listener',
        'click .tag_list li a span': 'remove_tag',
        'click .done_tagging_button': 'done_tagging',
        'click .add_tag_button': 'add_tag_button',
        'click .suggested_tags_holder li' : 'add_tag_suggestion',
        'submit form' : 'suppress_form_submission'
    },
    initialize: function(options) {
        // DON'T REMOVE .slice(). IT GUARANTEES A CLONE OF THE INPUT ARRAY
        this.tags = this.options.default_tags ? this.options.default_tags.slice(0) : []; // the set of tags
        this.sticky_tags = this.options.sticky_tags ? this.options.sticky_tags.slice(0) : []; // tags that cannot be removed
        // sticky tags is a subset of tags

		// Get all tags in use, or use suggested tags if options.suggestions exists
		var self = this;
		this.suggestions = [];

		if (!this.options.suggestions) {
			$.ajax({
				type: 'GET',
				url: site_root + '/api/v1/tag/',
				dataType: 'json',
				success: function(response_text) {
					var tags = response_text;
					for (var i = 0; i < tags.length; i++) {
						self.suggestions.push(tags[i].name);	
					}
				},
				error: function() {
					// Do we want to tell the user that we couldn't get suggested tags?
				}
			});
		}
		else {
			this.suggestions = this.options.suggestions ? this.options.suggestions.slice(0) : []; // things to put in the suggested tags list
		}

        this.tags_list = null; // the jQuery object representing the ul.tag_list element
        if (this.options.change)
            this.on('change', this.options.change);
        if (this.options.duplicate_rejected)
            this.on('duplicate_rejected', this.options.duplicate_rejected);
    },
    render: function() {
        this.$el.html(this.template({tags: this.tags}));
        this.tags_list = this.$el.find('.tag_list');
        this.tag_input = this.$el.find('.new_tag');
        this.suggestions_holder = this.$el.find('.suggested_tags_holder');
        this.$el.find('.tag_controls, .suggested_tags_holder').hide();
        return this;
    },
    set_editable: function(editable) {
        if (editable) 
            this.$el.find('li.edit_tags').show();
        else
            this.$el.find('li.tag_controls, li.edit_tags').hide();
    },
    /* Return the current tags as an array */
    get_tags: function() {
        return this.tags;
    },
    /* Listener for X button on tags */
    remove_tag: function(e) {
        var tag = $(e.currentTarget).closest('li').remove().attr('data-tag');
        this.tags = _.without(this.tags, tag);
        this.trigger('change', this.tags);
    },
    /* Listener for 'Done' button */
    done_tagging: function(e) {
        this.$el
            .find('.tag_controls').hide().end()
            .find('.edit_tags').show().end()
            .find('.tag_list li a span').remove();
    },
    /* Listener for 'Add' button */
    add_tag_button: function(e) {
        this.evaluate_input();
    },
    /* Listener for 'Edit Tags' button */
    edit_tags: function(e) {
        this.$el
            .find('.edit_tags').hide().end()
            .find('.tag_controls').show();

        var non_sticky = _.difference(this.tags, this.sticky_tags);

        // Put 'close' buttons on all of the non-sticky tags
        this.$el.find('.tag_list li').each(function(k, element) {
            if (_.contains(non_sticky, $(element).attr('data-tag')))
                $(element).find('a').append($('<span/>', {html: '&times;'}));
        });

        this.$el.find('.new_tag').focus();
    },
    /* Add a =sanitized= tag to the list of tags */
    add_tag: function(tag) {
        this.tags.push(tag);
        $('<li/>')
            .append("<a>"+tag+"<span>&times;</span></a>")
            .attr('data-tag', tag)
            .insertBefore(this.$el.find('.edit_tags'));
        this.trigger('change', this.tags);
    },
    /* Read the content of the tag input field; add tags appropriately. Validation and sanitization occurs here */
    evaluate_input: function() {
        var text = this.tag_input.val().toLowerCase();

        // strip invalid characters
        text = text.replace(/[^\._\-\/\+\[\]a-zA-Z0-9 ]/g, '').trim();

        // clear the input
        this.tag_input.val("");

        if (text.length > 0) {
            // Make sure tag isn't a duplicate before appending and updating db
            if (_.contains(this.tags, text)) {
                this.trigger('duplicate_rejected', text);
                this.$el.find('.new_tag').val("").focus();
                return;
            }
    
			var self = this;

            // Check to see if the tag already exists. If yes, add the tag, if not, ask user to describe tag, then add it.
            $.ajax({
                type: 'GET',
                url: site_root + '/api/v1/tag/' + text + '/', 
				statusCode: {
					200: function(response_text) {
						// Tag exists! Add it.
						self.add_tag(text);
					},
					404: function() {
						// Tag does not exist! Prompt the user to describe it, then add it.
						var header = 'Describe the tag "'+text+'"';
						var body = 'Please provide a concise, informative description of <strong>'+text+'</strong>.<br /><br /> <textarea style="width: 90%" rows="3" id="tag_desc"></textarea>';
						Atmo.Utils.confirm(header, body, {
							on_confirm: function() {
								
								var data = {};
								data["description"] = $('#tag_desc').val();
								data["name"] = text;

								$.ajax({
									type: 'POST',
									data: data,
									url: site_root + '/api/v1/tag/',
									success: function() {
										self.add_tag(text);
									},
									error: function() {
										var header = 'Could not create new tag';
										var body = 'If the problem persists, please email ' +
											'<a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>';

										Atmo.Utils.notify(header, body, { no_timeout: true });
									},
								});
									
							}	
						});
					}
				},
                dataType: 'json'
            });
        }
    },
    /* Listener for 'keyup' event on the tag input field */
    new_tag_input_listener: function(e) {
        // if the enter key or comma key was pressed
        if (e.keyCode == 13 || e.keyCode == 188) {
            e.preventDefault();
            this.evaluate_input();
            return false;
        }

        var text = this.tag_input.val().trim();
        if (text.length == 0) {
            this.suggestions_holder.empty().hide();
        } else {
            // rebuild suggestions list
            this.suggestions_holder.hide().empty();
            var suggestions = this.suggestions;

            // remove used suggestions from list
            suggestions = _.difference(suggestions, this.tags);

            suggestions = _.filter(suggestions, function(s) {
                return icontains(text, s); 
            });

            var self = this;
            if (suggestions.length > 0) {
                var d = {};
                _.each(suggestions, function(v, k) {
                    d[v] = Atmo.Utils.levenshtein_distance(text, v); 
                });
                suggestions.sort(function(a, b) {
                    return d[a] - d[b];
                });
                _.each(suggestions, function(suggestion) {
                    $('<li>')
                        .attr('data-tag', suggestion)
                        .append(suggestion)
                        .appendTo(self.suggestions_holder);            
                });

                this.suggestions_holder.show();
            }

        }
    },
    /* When a suggestion is clicked, add it */
    add_tag_suggestion: function(e) {
        var tag = $(e.currentTarget).attr('data-tag'); 
        this.suggestions_holder.hide();
        this.tag_input.val("").focus();
        this.add_tag(tag);
    },
    suppress_form_submission: function(e) {
        e.preventDefault();
        return false;
    }
});
