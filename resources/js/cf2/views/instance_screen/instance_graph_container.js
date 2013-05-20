/**
 *
 * Displays an instance's resource usage over time as a graph.
 *
 */
Atmo.Views.InstanceGraphContainer = Backbone.View.extend({
    on_failure: function() {
        this.$el.empty().append("<p>Metrics are not available for your instance.</p>");
    },
    render: function() {
        this.memory_graph = new Atmo.Views.InstanceMemoryGraph({
            model: this.model, 
            on_failure: _.bind(this.on_failure, this)
        });
        this.cpu_graph = new Atmo.Views.InstanceCPUGraph({
            model: this.model, 
            on_failure: _.bind(this.on_failure, this)
        });
        this.$el
            .append(this.memory_graph.render().el)
            .append(this.cpu_graph.render().el);
        google.load('visualization', '1', {packages:['corechart', 'controls'], callback: _.bind(this.draw_charts, this)});  
        return this;
    },
    draw_charts: function() {
        this.memory_graph.draw_chart();
        this.cpu_graph.draw_chart();
    },
    draw: function() {
        this.memory_graph.draw();
        this.cpu_graph.draw();
    }
});
