Number.prototype.toNumberCommaString = function() {
	return this.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

$(function() {


	//$('.carousel').carousel();

	var data = new Array();
	var most_saved = 0;
	var total_cpu_time = 0;

	$.ajax('/api/leaderboard', {
		type: 'GET',
		dataType: 'jsonp',
		async: false,
		statusCode: {
			200: function(response) {
				var results = JSON.parse(response.responseText);
				for (var i = 0; i < results.length; i++) {
					if (!results[i]["is_staff"]) {
						results[i]["total_cpu_time"] = Math.round(results[i]["total_cpu_time"]);

						data.push(results[i]);
						most_saved = (most_saved < results[i]["total_cpu_time"]) ? results[i]["total_cpu_time"] : most_saved;
						total_cpu_time += results[i]["total_cpu_time"];
					}

					if (data.length == 8)
						break;
				}
			}
		}
	});

	$('#total_cpu_time').html("" + Math.floor(total_cpu_time / 3600).toNumberCommaString());

	// Don't look at this, the code is uuuuugly

	var width = 200, height = 200, radius = Math.min(width, height) / 2;

	var color = d3.scale.ordinal()
		// Green Colors
		.range(['#73C65C','#43A84F','#009444','#006838']);

		// iPlant Colors
		//.range(['#0298AA', '#36B6B9', '#76AA42', '#456730']);

		// Default Colors
		//.range(["#98abc5", "#7b6888", "#6b486b", "#a05d56", "#d0743c"]);

	// Initial arcs, make them invisible so we can animate them as the data is added
	var arc = d3.svg.arc()
		.outerRadius(radius - 10)
		.innerRadius(radius - 10);

	var pie = d3.layout.pie()
		.sort(null)
		.value(function(d) {
			return d.total_cpu_time;
		});

	var svg = d3.select('#first_viz').append('svg')
		.attr('width', width + 200)
		.attr('height', height + 150)
		.append('g')
		.attr('transform', 'translate(' + ((width + 200) / 2) + ', ' + ((height + 150) / 2) + ')');

	// Build the graph
	var newArc = d3.svg.arc()
		.outerRadius(function(d) {
			var num = (d.data.total_cpu_time / most_saved) * 50;
			return radius + num;
		})
		.innerRadius(radius - 30);

	var g = svg.selectAll('.arc')
		.data(pie(data))
		.enter();

	var group =	g.append('g')
		.attr('class', 'arc');

	var path = g.append('path')
		.attr('d', arc)
		.style('fill', function(d) {
			return color(d.data.total_cpu_time);
		})
		.style('fill-opacity', 0.8);

	path.transition()
		.duration(500)
		.attr('d', newArc);

	path.on('mouseover', function(d) {
		var arcOver = d3.svg.arc()
			.outerRadius(function(d) {
				var num = (d.data.total_cpu_time / most_saved) * 50;
				return radius + num + 3;
			})
			.innerRadius(radius - 30);

		d3.select(this)
			.transition()
			.duration(250)
			.attr('d', arcOver)
			.style('fill-opacity', 1);
		
	});
	path.on('mouseout', function() {

		d3.select(this)
			.transition()
			.duration(250)
			.attr('d', newArc)
			.style('fill-opacity', 0.8);

	});

	var text = g.append('text')
		.attr('transform', function(d) {
		          return 'translate(' + arc.centroid(d) + ')';
		})
		.attr('dy', '.35em')
		.style('color', 'white')
		.style('text-anchor', 'middle')
		.text(function(d) {
			  return Math.floor(d.data.total_cpu_time / 3600).toNumberCommaString();
		});
});
