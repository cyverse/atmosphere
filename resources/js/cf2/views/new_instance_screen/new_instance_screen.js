/* New Instance view */
Atmo.Views.NewInstanceScreen = Backbone.View.extend({
    tagName: 'div',
    className: 'screen',
    id: 'imageStore',
    events: {
        'click .clear_search': 'clear_search',
        'change #image_search': 'filter_image_list',
        'keyup #image_search': 'filter_image_list',
        'click .image_list > li': 'img_clicked',
        'click #launchInstance': 'launch_instance',
        'keyup #newinst_name' : 'validate_name',
        //'dblclick .image_list > li' : 'quick_launch',
        'click #help_request_more_resources2' : 'show_request_resources_modal',
    },
    template: _.template(Atmo.Templates.new_instance_screen),
    initialize: function(options) {
        Atmo.images.bind('reset', this.render_image_list, this);
        Atmo.images.bind('fail', this.report_error_image_list, this);
        Atmo.instances.bind('add', this.render_resource_charts, this);
        Atmo.instances.bind('remove', this.render_resource_charts, this);
        Atmo.instances.bind('change:state', this.render_resource_charts, this);
        Atmo.instance_types.bind('change:selected', this.update_resource_charts, this);
        this.launch_lock = false;
        this.under_quota = true;
        this.init_query = options['query'] ? options['query'] : null;
        this.tagger = null;
    },
    render: function() {
        this.$el.html(this.template({
            'is_staff':Atmo.profile.get('is_staff')}));

        this.mem_resource_chart = new Atmo.Views.ResourceCharts({
            el: this.$el.find('#memHolder'),
            quota_type: 'mem',
        }).render();
        this.cpu_resource_chart = new Atmo.Views.ResourceCharts({
            el: this.$el.find('#cpuHolder'),
            quota_type: 'cpu'
        }).render();
        if (Atmo.profile.attributes.selected_identity.has_allocation()) {
            this.time_resource_chart = new Atmo.Views.ResourceCharts({
                el: this.$el.find('#allocationHolder'),
                quota_type: 'allocation'
            }).render();
        } else {
            graph_holders = this.$el.find('#resource_usage_holder');
            alloc_graph = this.$el.find("#allocationHolder").parent();
            alloc_graph.remove();
            graph_holders.children().each( function() {
                $(this).removeClass('col-sm-4').addClass('col-sm-6');
            });
        }

        // Make the dropdown functional
        this.$el.find('a[data-target="advanced_options"]').click(function() {
            $('#advanced_options').collapse('toggle');
        });
        this.$el.find('#advanced_options').on('show', function() {
            $('a[data-target="advanced_options"]').addClass('dropup');
        });
        this.$el.find('#advanced_options').on('hide', function() {
            $('a[data-target="advanced_options"]').removeClass('dropup');
        });

        this.render_image_list();
        this.render_instance_type_list();

        // Assign content to the popovers
        this.$el.find('#allocationHolder').popover({
            placement: 'bottom',
            trigger: 'hover',
            title: 'Time Allocation <a class="close" data-dismiss="popover" href="#new_instance" data-parent="help_image">&times</a>',
            html: true,
            content: function() {
                allocation = Atmo.profile.attributes.selected_identity.attributes.quota.allocation;
                hours_remaining = Math.floor(allocation.ttz / 60);
                burn_time = Math.floor(allocation.burn / 60);
                var content = 'The graph above represents the <b>time you have currently used</b> for this provider.<br /><br />';
                content += 'As of now, you have <b>' + hours_remaining + ' hours remaining.</b><br /><br />';
                if (burn_time != 0) {
                    content += "Given your current instance configuration, you will <b>run out of ALL your time in " + burn_time + ' hours</b>';
                }
                return content;
            }
        }).click(this.x_close);
        this.$el.find('#help_image').popover({
            placement: 'bottom',
            title: 'Select an Image <a class="close" data-dismiss="popover" href="#new_instance" data-parent="help_image">&times</a>',
            html: true,
            content: function() {
                var content = 'An <b>image</b> is a template for an instance. The operating system, configuration, and software that comes pre-installed on your instance will depend on which image you choose.<br /><br />';
                content += 'An <b>instance</b> is a specific virtual machine with dedicated RAM, CPUs, and disk space, which exists on a physical compute node. You can use an instance as you would use a physical computer for most tasks.<br /><Br />';
                content += 'To launch an instance, first <b>choose an image</b>, then configure it if you\'d like. ';
                content += '(<a href="https://pods.iplantcollaborative.org/wiki/x/Lqxm" target="_blank">More information</a>)';
                return content;
            }
        }).click(this.x_close);
        this.$el.find('#help_image_search').popover({
            placement: 'right',
            title: 'Search Images <a class="close" data-dismiss="popover" href="#new_instance" data-parent="help_image_search">&times</a>',
            html: true,
            content: function() {
                var content = 'You can search images by name, description, or <br />emi number.<br /><br />';
                content += 'You can also search by tag using the syntax <br /> <em>tag:tag_to_find</em>.';
                return content;
            }
        }).click(this.x_close);
        this.$el.find('#help_resource_usage_newinst').popover({
            placement: 'bottom',
            title: 'My Projected Resource Usage <a class="close" data-dismiss="popover" href="#new_instance" data-parent="help_resource_usage_newinst">&times</a>',
            html: true,
            content: function() {
                var content = 'Your <strong>projected resource usage</strong> is determined by how many CPUs and GB of memory you would use by launching an new instance, including any resources your other instances are already using. <br /><br />';
                content += 'If you don\'t have enough resources to launch your preferred instance size, you can terminate a running instance or request more resources.';
                return content;
            }
        }).click(this.x_close);
        return this;
    },
    x_close: function() {

            // Must assign this function after the popover is actually rendered, so we find '.close' element
            $('.close').click(function(e) {
                e.preventDefault();
                var popover_parent = $(this).data('parent');
                if (popover_parent != undefined) {
                    $('#'+popover_parent).popover('hide');
                }
            });
    },
    render_resource_charts: function() {
        if (Atmo.profile.attributes.selected_identity.has_allocation()) {
            this.time_resource_chart.render();
        }
        this.mem_resource_chart.render();
        this.cpu_resource_chart.render();
        this.$el.find('#newinst_size').trigger('change');
    },
    render_image_list: function() {
        var self = this;
        if(Atmo.images.models.length == 0) {
            // Called when images haven't yet loaded
            self.$el.find('#featured_image_list').append('<div style="text-align: center"><img src="'+site_root+'/resources/images/loader_large.gif" /></div>');
            self.$el.find('#misc_image_list').append('<div style="text-align: center"><img src="'+site_root+'/resources/images/loader_large.gif" /></div>');
        }
        else {

            // Called when 'reset' is triggered because images have been fetched
            self.$el.find('#featured_image_list').html('');
            self.$el.find('#misc_image_list').html('');

            $.each(Atmo.images.models, function(i, image) {
                if (image.get('featured'))
                    self.$el.find('#featured_image_list').append(new Atmo.Views.ImageListItem({model: image}).render().el);
                else
                    self.$el.find('#misc_image_list').append(new Atmo.Views.ImageListItem({model: image}).render().el);
            });

            if (this.init_query)
                this.set_query(this.init_query);

            // Make all the tags clickable so they search for that tag when clicked

            var tag_els = this.$el.find('#image_holder .tag_list').children();
            $.each(tag_els, function(i, tag) {
                $(tag).click(function() {
                    var tag_name = "tag:"+$(tag).text();
                    var search_obj = self.$el.find('#image_search');
                    var search_txt = $.trim(search_obj.val());
                    if(search_txt.search(tag_name) == -1) {
                        add_tag = search_txt.length == 0 ? tag_name : " "+tag_name;
                        search_obj.val(search_txt+add_tag);
                    }
                    self.filter_image_list();
                });
            });
        }

        resizeApp();
    },
    report_error_image_list: function() {

        this.$el.find('#featured_image_list').html('');
        this.$el.find('#misc_image_list').html('<p class="alert alert-error"><strong>Error</strong> Could not load images.</p><p>Refresh the application to try again. Contact support if the problem persists.</p>');
    },
    set_query: function(query) {
        this.$el.find('#image_search').val(query);
        this.filter_image_list();
    },
    render_instance_type_list: function() {
        if (Atmo.profile.get('is_staff') === true) {
            new Atmo.Views.HypervisorDropdown({
                el: this.$el.find('#newinst_hypervisor')[0]
            }).render();
        }
        new Atmo.Views.InstanceSizeDropdown({
            el: this.$el.find('#newinst_size')[0]
        }).render();
    },
    update_resource_charts: function() {
        var selected_instance_type = Atmo.instance_types.selected_instance_type;

        //if (Atmo.instances.models.length == 0)
        var under_cpu = this.cpu_resource_chart.add_usage(
            selected_instance_type.attributes.cpus,
            {
                is_initial: Atmo.instances.models.length == 0
            }
        );
        var under_mem = this.mem_resource_chart.add_usage(
            selected_instance_type.attributes.mem,
            {
                is_initial: Atmo.instances.models.length == 0
            }
        );
        if (self.time_resource_chart) {
            var under_time = this.time_resource_chart.add_usage(0,{});
        } else {
            var under_time = true;
        }

        if ((under_cpu == false) || (under_mem == false) || (under_time == false)) {
            this.$el.find('#launchInstance').attr('disabled', 'disabled');
            this.under_quota = false;
        }
        else {
            if ($('.image_list > li').hasClass('active') && !this.launch_lock) {
                this.$el.find('#launchInstance').removeAttr('disabled');
            }
            this.under_quota = true;
        }

        var select_obj = this.$el.find('#newinst_size');
        select_obj.parent().find('.help-block').remove();

        if (!this.under_quota) {
            select_obj.parent().append($('<div/>', {
                'class': 'help-block',
                html: 'Launching this instance would exceed your quota. Select a smaller size or terminate another instance.'
            }));
            select_obj.closest('.control-group').addClass('error');
        }
        else {

            if (select_obj.parent().find('.help-block').length > 1) {
                select_obj.parent().find('.help-block').remove();
            }
            select_obj.closest('.control-group').removeClass('error');

        }

    },
    clear_search: function() {
        this.$el.find('#image_search').val('').trigger('keyup');
    },
    filter_by_tag: function(tag) {

        this.$el.find(".image_list > li").hide();
        //this.$el.find(".image_list li:icontains("+text+")").show();

        $.each(this.$el.find('.image_list > li'), function(i, e) {
            var found = false;
            var testImage = $(e).data('image');

            var tags = testImage.get('tags');
            $.each(tags, function(idx, el_tag) {
                found = found || (el_tag == tag);
                if(found){
                    return;
                }
            });

            if (found) $(e).show();
        });
    },
    filter_image_list: function(e) {
        /** Quick text validation*/
        var text = this.$el.find('#image_search').val();
        if (text.match(/[^\:\._\-\/\+\[\]\,a-zA-Z0-9 ]/g)) {
            this.$el.find('#image_search').val(text.replace(/[^\:\._\-\/\+\[\]\,a-zA-Z0-9 ]/g, ''));
        }
        text = this.$el.find('#image_search').val();
        if (text.length !== 0) {

            /**Filter out those who don't contain text*/
            this.$el.find(".image_list > li").hide();
            arr = text.split(/\s+/g);
            tags = [];
            words = [];
            $.each(arr, function(i, word) {
                try {
                    patt = /tag:(\w+)/gi; //Hacky? Must be re-init every time to avoid false negatives
                    match = patt.exec(word);
                    tags.push(match[1]);
                } catch(err) {
                    words.push(word);
                }
            });

            $.each(this.$el.find('.image_list > li'), function(i, e) {
                var found = true;

                var testImage = $(e).data('image');
                var test_tags = testImage.get('tags');

                // To make the search case-insensitive
                for (var i = 0; i < test_tags.length; i++) {
                    test_tags[i] = test_tags[i].toLowerCase();
                }

                var test_id   = testImage.id;
                var test_name = testImage.get('name');
                var test_desc = testImage.get('description');


                $.each(tags, function(idx,tag) {
                    // Can't just test against the whole array, or will only get complete matches
                    //var tag_idx = test_tags.indexOf(tag.toLowerCase());

                    var found_one = false;

                    // Need to test for partial matches -- already a ton of nested loops, why not one more!!!
                    for (var i = 0; i < test_tags.length; i++) {
                        if (test_tags[i].indexOf(tag.toLowerCase()) == -1) {

                            // If already found one tag, keep found_one true.
                           found_one = (found_one == true) ? true : false;
                        }
                        else {
                            found_one = true;
                        }
                    }
                    if (!found_one) {
                        found = false;
                        return;
                    }
                });
                $.each(words, function(idx,word) {
                    word = word.toLowerCase();
                    if (! test_name.toLowerCase().find(word) && ! test_desc.toLowerCase().find(word) && ! test_id.toLowerCase().find(word)) {
                        found = false;
                        return;
                    }
                });
                if (found) $(e).show();
            });
        } else {
            this.$el.find(".image_list > li").show();
        }
    },
    img_clicked: function(e) {
        var img = $(e.currentTarget).data('image');
        //Backbone.history.navigate('#images/' + img.get('id'));
        $('.image_list > li').removeClass('active');
        $(e.currentTarget).addClass('active');
                if (this.under_quota && !this.launch_lock) {
                    this.$el.find('#launchInstance').removeAttr('disabled');
                } else {
                    this.$el.find('#launchInstance').attr('disabled', true);
                }
        this.$el.find('#selected_image_icon_container').html('<img src="'+img.get('image_url')+'" width="50" height="50"/>');
        this.$el.find('#selected_image_description')
            .html(img.get('description'));
        this.$el.find('#newinst_name_title').html('of ' + img.get('name_or_id'));
        this.$el.find('#newinst_name').val(img.get('name_or_id'));

        // Validate name
        this.$el.find('#newinst_name').trigger('keyup');

        // Make the tags fancy
        var tags_array = img.get('tags');

        this.tagger = new Atmo.Views.Tagger({
            default_tags: tags_array,
            sticky_tags: tags_array
        });

        this.$el.find('#newinst_tags')
            .empty()
            .append(this.tagger.render().el);

        this.$el.find('#newinst_owner')
            .attr('disabled', 'disabled')
            .val(img.get('ownerid'));

        this.$el.find('#newinst_createdate')
            .attr('disabled','disabled')
            .val(img.get('create_date').toString("MMM d, yyyy"));

        this.$el.find('#newinst_image_id').val(img.get('id'))
    },
    quick_launch: function(e) {
        // Emulate selection
        launch_setting = Atmo.profile.attributes['settings'].quick_launch;
        if (launch_setting == false) {
            Atmo.Utils.notify("Quicklaunch Disabled", "Quicklaunch has been disabled. Edit your settings to re-enable.");
            return;
        }
        this.img_clicked(e);

        this.$el.find('#launchInstance').trigger('click');

    },
    launch_instance: function(e) {
        e.preventDefault();

        var form = this.$el.find('#image_customlaunch form')[0];
            var image = Atmo.images.get($(form.image_id).val());

        var params = {
          'machine_alias': image.get('id'),
          'size_alias': $(form.newinst_size).val(),
          'name': $(form.name).val(),
          'tags': this.tagger.get_tags()
        };

        var error_elements = [];
        var errors = [];

        this.$el.find('.error').removeClass('error');
        this.$el.find('.help-inline').remove();

        var nameText = params['name'];
        if(nameText.length === 0) {
            error_elements.push(form.name);
            errors.push('Enter a name for your instance');
        }

        if (errors.length == 0) {
            var header = '<img src="../resources/images/loader_bluebg.gif" /> Launching Instance...';
            var body = '';
            Atmo.Utils.notify(header, body, { no_timeout : true});

            // Prevent launching one instance while another is just launched
            this.launch_lock = true;
            var instance = new Atmo.Models.Instance();
            var self = this;
            $('#launchInstance')
                .attr('disabled', 'disabled')
                .val('Launching Instance...')
                .after($('<div/>', {'class': 'loader'}));
            instance.save(params, {
                wait: true,
                success: function(model) {
                        Atmo.instances.update({success: function() {
                                        self.launch_lock = false;
                            Atmo.instances.get(model.id).select();
                    }});
                    window.app.navigate('instances', {trigger: true, replace: true});
                    self.render();
                                Atmo.Utils.notify("Instance Launched", "Your instance will be ready soon.");
                },
                error: function(model,xhr,options) {
                    if(xhr.status < 500){
                       responseText = jQuery.parseJSON(xhr.responseText);
                       Atmo.Utils.notify("Instance launch could not be completed for the following errors:", ''+ responseText.errors[0].message  + ' If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
                    }
                    else{
                       Atmo.Utils.notify("Instance launch was unsuccessful", 'If the problem persists, please email <a href="mailto:support@iplantcollaborative.org">support@iplantcollaborative.org</a>', { no_timeout: true });
                    }
                    // Allow user to try launching again
                    self.launch_lock = false;
                    $('#launchInstance')
                        .removeAttr('disabled')
                        .val('Launch Instance');

                },
            });
        } else {
            $.each(error_elements, function(i, e) {
                $(e).closest('.control-group').addClass('error');
                $(e).after($('<p>', {'class': 'help-inline', html: errors[i]}));
            });
        }

        return false;
    },
    validate_name: function() {
        var instance_name = this.$el.find('#newinst_name').val();
        var instance_name_input = this.$el.find('#newinst_name');

        // Get rid of any pre-existing error message on next key up
        if (instance_name_input.parent().children().length > 1) {
            instance_name_input.parent().children().eq(1).remove();
            instance_name_input.closest('.control-group').removeClass('error');
        }

        if (instance_name.length < 1 || instance_name.trim().length < 1) {
            instance_name_input.parent().append($('<div/>', {
                'class': 'help-block',
                html: 'Instance name cannot be blank'
            }));
            instance_name_input.closest('.control-group').addClass('error');
        }
        else {
            if (instance_name_input.parent().children().length > 1) {
                instance_name_input.parent().children().eq(1).remove();
            }
            instance_name_input.closest('.control-group').removeClass('error');
        }
    },
    show_request_resources_modal: function() {
        Atmo.request_resources_modal.do_alert();
    },
    hide_burn_time: function() {
    },
    show_burn_time: function() {
    }
});
