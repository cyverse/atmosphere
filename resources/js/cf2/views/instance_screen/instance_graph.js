Atmo.Views.InstanceGraph = Backbone.View.extend({
    events: {
    },
    initialize: function() {
        this.stop = new Date();
        this.range = 2*24*60*60*1000; // 48 hour range
        this.start = new Date(this.stop.valueOf() - this.range);
        this.data = null;
        $(window).bind('resize', _.bind(this.draw, this));
    },
    data_request: function(callback) {
        if (this.data != null)
            callback(this.data);
        else {
            var self = this;
            $.ajax({
                url: site_root + '/instance_graph',
                data: {
                    instance_id: this.model.get('id'),
                    start: this.start.toISOString()
                },
                type: 'GET',
                dataType: 'json',
                success: function(data, textStatus) {
                    if (data instanceof Object) {
                        var new_data = {};
                        _.each(['load', 'memory', 'disk'], function(v, k) {
                            new_data[v] = _.filter(data[v], function(d) {return d.value != undefined});
                        });
                        self.data = self.merge_metrics(new_data);
                        //console.log('ROWS', self.data, self.data.length);
                        if (self.data.length >= 3) 
                            callback(self.data);
                        else
                            self.on_failure();
                    }
                },
                error: function() {
                    self.on_failure();
                }
            });
        }
    },
    on_failure: function() {
        this.$el.empty().append("<p>Metrics are not available for your instance.</p>");
    },
    render: function() {
        this.$el
            .append($("<div>", {id: "chart-" + this.model.get('id')}).css('height', '220px'))
            .append($("<div>", {id: "control-" + this.model.get('id')}).css('height', '40px'));
        google.load('visualization', '1', {packages:['corechart', 'controls'], callback: _.bind(this.draw_chart, this)});  
        return this;
    },
    /**
     * Utility function for merging data measured on independent time axes
     * For example, consider your data is formatted as three objects as time: value pairings
     * merge_metrics({k1: [{time: a, value: 1}, {time: b, value: 2}], k2: [{time: b, value: 3}, {time: c, value: 4}], k3: [{time: c, value: 5}]}); should return 
     * [{time: a, k1: 1}, {time: b, k1: 2, k3: 3}, {time: c, k2: 4, k3: 5}]
     */
    merge_metrics: function(data) {
        var formatted_data = {};

        _.each(data, function(values, m) {
            _.each(values, function(v, t) {
                if (formatted_data[v.time] == undefined)
                    formatted_data[v.time] = {};        
                formatted_data[v.time][m] = v.value;
            });
        });

        var return_data = [];
        _.each(formatted_data, function(v, t) {
            return_data.push(_.extend({time: t}, v)) ;
        });
        
        var sorted_return_data = _.sortBy(return_data, function(v) {return v.time});
        //console.log(sorted_return_data);
        return sorted_return_data;
    },
    draw_chart: function() {
        this.dashboard = new google.visualization.Dashboard(this.el);

        //console.log('LOOK AT ME', this.start, this.stop);

        var control = new google.visualization.ControlWrapper({
            'controlType': 'ChartRangeFilter',
            'containerId': 'control-' + this.model.get('id'),
            'options': {
                // Filter by the date axis.
                'filterColumnIndex': 0,
                'ui': {
                    'chartType': 'LineChart',
                    'chartOptions': {
                        'chartArea': {'width': '80%'},
                        'hAxis': {'baselineColor': 'none', /*'minValue': this.start*/},
                        'vAxis': {'maxValue': 1, 'minValue': 0},
                        'backgroundColor': 'transparent',
                        'interpolateNulls': true
                    },
                    // Display a single series that shows the closing value of the stock.
                    // Thus, this view has two columns: the date (axis) and the stock value (line series).
                    'chartView': {
                        'columns': [0, 1]
                    },
                    // 1 hour in milliseconds = 60 * 60 * 1000 = 36e5
                    'minRangeSize': 36e5
                }
            },
            'state': {'range': {'start': this.start, 'end': this.stop}}
        });

        var chart = new google.visualization.ChartWrapper({
            'chartType': 'LineChart',
            'containerId': 'chart-' + this.model.get('id'),
            'options': {
                // Use the same chart area width as the control for axis alignment.
                'chartArea': {'height': '80%', 'width': '80%'},
                'hAxis': {'slantedText': false},
                'vAxes': {
                    "0": {'format': '#,###%', 'title': 'RAM, Used Disk Space (%)', 'maxValue': 1, 'minValue': 0},
                    "1": {'title': 'CPU Load', 'maxValue': 1, 'minValue': 0}
                },
                'legend': {'position': 'top'},
                'series': {
                    "0": {'targetAxisIndex': 1},
                    "1": {'targetAxisIndex': 0},
                    "2": {'targetAxisIndex': 0}
                },
                'backgroundColor': 'transparent',
                'interpolateNulls': true
            },
            // Convert the first column from 'date' to 'string'.
            'view': {
                'columns': [
                    {
                        'calc': function(dataTable, rowIndex) {
                             return dataTable.getFormattedValue(rowIndex, 0);
                        },
                        'type': 'string'
                    }, 1, 2, 3
                ]
            }
        });

        var self = this;
        this.data_request(function(data) {
            //console.log(data); 
            self.table = new google.visualization.DataTable();
            self.table.addColumn('date', 'Date');
            self.table.addColumn('number', 'CPU Load');
            self.table.addColumn('number', 'RAM');
            self.table.addColumn('number', 'Used Disk Space');

            var rows = _.map(data, function(d) {
                return [new Date(d.time), d.load, d.memory, d.disk];
            });
            self.table.addRows(rows);

            var date_formatter = new google.visualization.DateFormat({pattern: 'MMM d h:mm a'});
            date_formatter.format(self.table, 0);
            var percentage_formatter = new google.visualization.NumberFormat({pattern: '###%'});
            percentage_formatter.format(self.table, 2);
            percentage_formatter.format(self.table, 3);

            //console.log(self.table);

            self.dashboard.bind(control, chart);
            self.dashboard.draw(self.table);
        });
    },
    draw: function() {
        if (this.dashboard)
            this.dashboard.draw(this.table);
    }
});
