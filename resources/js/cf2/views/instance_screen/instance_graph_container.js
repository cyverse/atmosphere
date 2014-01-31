/**
 *
 * Displays an instance's resource usage over time as a graph.
 *
 */
Atmo.Views.InstanceGraphContainer = Backbone.View.extend({
    template: _.template(Atmo.Templates.instance_graph_container),
    events: {
        'shown .nav a': 'select_tab'
    },
    on_failure: function() {
        this.$el.empty().append("<p>Metrics are not available for your instance.</p>");
    },
    render: function() {
        if (typeof google === 'undefined')
            return this;

        try {
            this.memory_graph = new Atmo.Views.InstanceMemoryGraph({
                model: this.model, 
                on_failure: _.bind(this.on_failure, this)
            });
            this.cpu_graph = new Atmo.Views.InstanceCPUGraph({
                model: this.model, 
                on_failure: _.bind(this.on_failure, this)
            });
        } catch(err) {
            this.on_failure();
            return this;
        }

        this.$el
            .html(this.template())
            .find('.tab-content')
                .append(this.memory_graph.render().el)
                .append(this.cpu_graph.render().el)
            .end()
            .find('.tab-pane:eq(0)').addClass('active').end()
            .find('.nav')
                .find('a:eq(0)')
                    .attr('href', '#' + 'instance_graph_memory_' + this.model.get('id'))
                    .data('graph', this.memory_graph)
                    .end()
                .find('a:eq(1)')
                    .attr('href', '#' + 'instance_graph_cpu_' + this.model.get('id'))
                    .data('graph', this.cpu_graph)
                    .end()
            .end();

        google.load('visualization', '1', {packages:['corechart', 'controls'], callback: _.bind(this.draw_charts, this)});  
        return this;
    },
    draw_charts: function() {
        if (this.memory_graph && this.cpu_graph) {
            this.memory_graph.draw_chart();
            this.cpu_graph.draw_chart();
        }
    },
    draw: function() {
        if (this.memory_graph && this.cpu_graph) {
            this.memory_graph.draw();
            this.cpu_graph.draw();
        }
    },
    select_tab: function(e) {
        var graph = $(e.target).data('graph');
        graph.draw();
    }
});
