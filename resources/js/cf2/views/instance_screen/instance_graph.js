/**
 *
 * Displays an instance's resource usage over time as a graph.
 *
 */
Atmo.Views.InstanceGraph = Backbone.View.extend({
    events: {
    },
    initialize: function() {
        this.stop = new Date();
        this.range = 7*24*60*60*1000; // seven days
        this.start = new Date(this.stop.valueOf() - this.range);
        this.data = {'cpu': null, 'memory': null};
        $(window).bind('resize', _.bind(this.draw, this));

        var provider_id = Atmo.profile.get('selected_identity').get('provider_id')
        this.selected_provider = Atmo.providers.get(provider_id)
    },
    data_request: function(type, callback) {
        if (this.data[type] != null)
            callback(this.data[type]);
        else {
            var self = this;
            $.ajax({
                url: site_root + '/api/metrics',
                data: {
                    id: this.model.get('id'),
                    provider: this.selected_provider.get('type'),
                    from: '-7d',
                    type: type
                },
                type: 'GET',
                dataType: 'json',
                success: function(data, textStatus) {
                    console.log(data);
                    self.data[type] = data;
                    if (self.data[type].length >= 3) 
                        callback(self.data[type]);
                    else
                        self.on_failure();
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
        var self = this;
        var chart_area = function(type) {
            return $('<div>')
                .addClass('chart-' + type)
                .append($("<div>", {id: "chart-" + type + '-' + self.model.get('id')}).css('height', '220px'))
                .append($("<div>", {id: "control-" + type + '-' + self.model.get('id')}).css('height', '40px'));
        };
        this.$el
            .append(chart_area('memory'))
            .append(chart_area('cpu'));
        google.load('visualization', '1', {packages:['corechart', 'controls'], callback: _.bind(this.draw_charts, this)});  
        return this;
    },
    draw_charts: function() {
        var memory_columns = [
            ['number', 'Active'], 
            ['number', 'Inactive'], 
            ['number', 'Free']
        ];
        var memory_row_formatter = function(d) {
            return [
                new Date(d.time * 1000), 
                d['memory.active'] / 1024, 
                d['memory.inactive'] / 1024, 
                d['memory.free'] / 1024
            ];
        };
        this.memory_dashboard = new google.visualization.Dashboard(this.$el.find('.chart-memory')[0]);
        this.draw_chart(this.memory_dashboard, 'memory', 'Memory (MB)', memory_columns, memory_row_formatter);

        var cpu_columns = [
            ['number', 'User'], 
            ['number', 'System'], 
            ['number', 'Idle'], 
            ['number', 'Waiting for IO']
        ];
        var cpu_row_formatter = function(d) {
            return [
                new Date(d.time * 1000),
                d['cpu.user'],
                d['cpu.system'],
                d['cpu.idle'],
                d['cpu.waiting']
            ];
        };
        this.cpu_dashboard = new google.visualization.Dashboard(this.$el.find('.chart-cpu')[0]);
        this.draw_chart(this.cpu_dashboard, 'cpu', 'CPU time (%)', cpu_columns, cpu_row_formatter);
    },
    draw_chart: function(dashboard, type, vaxis_title, columns, row_formatter) {
        //this.dashboard = new google.visualization.Dashboard(el[0]);

        //console.log('LOOK AT ME', this.start, this.stop);

        var control = new google.visualization.ControlWrapper({
            'controlType': 'ChartRangeFilter',
            'containerId': 'control-' + type + '-' + this.model.get('id'),
            'options': {
                // Filter by the date axis.
                'filterColumnIndex': 0,
                'ui': {
                    'chartType': 'LineChart',
                    'chartOptions': {
                        'chartArea': {'width': '80%'},
                        'hAxis': {'baselineColor': 'none'},
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
            'chartType': 'SteppedAreaChart',
            'containerId': 'chart-' + type + '-' + this.model.get('id'),
            'options': {
                // Use the same chart area width as the control for axis alignment.
                'isStacked': true,
                'chartArea': {'height': '80%', 'width': '80%'},
                'hAxis': {'slantedText': false},
                'vAxes': {
                    "0": {'title': vaxis_title}
                },
                'legend': {'position': 'top'},
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
        this.data_request(type, function(data) {
            //console.log(data); 
            self.table = new google.visualization.DataTable();
            self.table.addColumn('date', 'Date');
            _.each(columns, function(d) {
                self.table.addColumn(d[0], d[1]);
            });

            var rows = _.map(data, row_formatter);
            
            console.log(rows);
            self.table.addRows(rows);

            var date_formatter = new google.visualization.DateFormat({pattern: 'MMM d h:mm a'});
            date_formatter.format(self.table, 0);

            dashboard.bind(control, chart);
            dashboard.draw(self.table);
        });
    },
    draw: function() {
        if (this.dashboard)
            this.dashboard.draw(this.table);
    }
});
