function createV4DraggableGraph(svg, graph) {
    // if both d3v3 and d3v4 are loaded, we'll assume
    // that d3v4 is called d3v4, otherwise we'll assume
    // that d3v4 is the default (d3)
    if (typeof d3v4 == 'undefined')
        d3v4 = d3;

    var width = +svg.attr("width"),
        height = +svg.attr("height");

    let parentWidth = d3v4.select('svg').node().parentNode.clientWidth;
    let parentHeight = d3v4.select('svg').node().parentNode.clientHeight;

    var svg = d3v4.select('svg')
    .attr('width', parentWidth)
    .attr('height', parentHeight)

    // remove any previous graphs
    svg.selectAll('.g-main').remove();

    var gMain = svg.append('g')
    .classed('g-main', true);

    var rect = gMain.append('rect')
    .attr('width', parentWidth)
    .attr('height', parentHeight)
    .style('fill', 'white')

    var gDraw = gMain.append('g');

    var zoom = d3v4.zoom()
        .on('zoom', zoomed);

    gMain.call(zoom)
        .on("dblclick.zoom", null) // disable double-click to zoom  https://github.com/d3/d3-zoom/blob/master/README.md#zoom_duration

    function zoomed() {
        gDraw.attr('transform', d3v4.event.transform);
    }

    //var color = d3v4.scaleOrdinal(d3v4.schemeCategory20);

    if (! ("links" in graph)) {
        console.log("Graph is missing links");
        return;
    }

    var params = {
        link_quantile_method: 'radius_threshold',
        link_quantile: 0.5,
        max_radius: 10.,
        min_radius: 3.,
        radius_decay: 0.1,
    };

    var link_map = new Map();
    for (let link of graph.links) {
        link_map.set([link.source, link.target].join(','), link)
        link_map.set([link.target, link.source].join(','), link)
    }

    var node_map = new Map();
    for (let node of graph.nodes) {
        node_map.set(node.name, node)
    }

    var sim_scores_sorted = []
    for (let link in graph.links) {
        sim_scores_sorted.push(link.sim_score);
    }
    sim_scores_sorted.sort();

    var radius_scores_sorted;
    _updateRadii()

    var links = gDraw.append("g")
        .attr("class", "link")
        .selectAll("link")
        .data(graph.links)
        .enter().append("line")
        //TODO
        //.attr("stroke-width", d => d.stroke_width );
        .attr("stroke-width", 1.5);

    var nodes = gDraw.append("g")
        .attr("class", "node")
        .selectAll("node")
        .data(graph.nodes)
        .enter().append("circle")
        .attr("r", d => d.radius)
        .on("dblclick", node_double_clicked)
        .call(d3v4.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    var nodes_text = gDraw.append("g")
        .attr("class", "node_text")
        .selectAll("text")
        .data(graph.nodes)
        .enter().append("text")
        .attr("x", node => node.radius+2)
        .attr("y", ".31em")
        .text(function(d) { return d.name; });

    nodes.append("title")
        .text(d => d.name);

    links.append("title")
        .text(function(link) {
            s = link.source + ' similar to ';
            s += link.target + ' with ' + link.sim_score + ' votes';
            return s;
        })

    // initialize properties we'll use for interaction with the nodes & links
    nodes.each(function(node) {
        node.radius = params.min_radius;
        node.selected = false;
        node.hidden = false;
        node.fixed = false;
        })

    links.each(function(link) {
        link.hidden = false;
        link.user_hidden = false;
        })

    nodes_text.each(function(text) {
        text.hidden = false;
        })

    var simulation = d3v4.forceSimulation()
        .stop()
        .alphaMin(0.05)
        .force("link", d3v4.forceLink()
                .id(function(d) { return d.name; })
                //.distance(50)
                .strength(0.01)
              )
        .force("charge", d3v4.forceManyBody()
                //.strength(-50)
                //.strength(node => Math.min(-20, Math.max(-30, -20./Math.sqrt(node.radius))))
                .distanceMin(20)
                //.distanceMax(200)
            )
        //.force("collide", d3v4.forceCollide()
        //        .radius(10))
        .force("center", d3v4.forceCenter(0.5*parentWidth, 0.7*parentHeight))
        .force("x", d3v4.forceX(0.5*parentWidth).strength(0.05))
        .force("y", d3v4.forceY(parentHeight).strength(0.05))
        //.force("radial", d3v4.forceRadial()
        //    .radius(300)
        //    .x(parentWidth/2)
        //    .y(parentHeight/2)
        //    .strength(function(node) { return 0.1; }))

    simulation
        .nodes(graph.nodes)
        .on("tick", ticked);

    simulation.force("link")
        .links(graph.links);


    function ticked() {
        // update node and line positions at every step of
        // the force simulation
        links.attr("x1", function(d) { return d.source.x; })
            .attr("y1", function(d) { return d.source.y; })
            .attr("x2", function(d) { return d.target.x; })
            .attr("y2", function(d) { return d.target.y; });

        nodes.attr("cx", function(d) { return d.x; })
            .attr("cy", function(d) { return d.y; });

        nodes_text.attr("transform", d => "translate(" + d.x + "," + d.y + ")")
    }

    rect.on('click', () => {
        nodes.each(node => node.selected = false)
            .classed("selected", false);
        links.each(link => link.selected = false)
            .classed("selected", false);
    });

    function dragstarted(d) {
        if (!d3v4.event.active) simulation.alphaTarget(0.9).restart();

        if (!d.selected) {
            // if this node isn't selected, then we have to unselect every other node
            nodes.classed("selected", function(node) {
                node.selected = false;
                return false;
            });
        }

        // Set links that source from this node to selected
        links.filter((link) => link.source.name == d.name || link.target.name == d.name)
            .each(function(link) {
                link.selected = true;
                link.hidden = false;
                link.user_hidden = false;
            })

        // Set the selected class for this node and links
        d3v4.select(this).classed("selected", (d) => d.selected = true);

        // Unselect the other links
        links.filter((link) => link.source.name != d.name && link.target.name != d.name)
            .classed("selected", false)

        links.filter((link) => link.selected)
            .classed("selected", true)
            .classed("hidden", link => link.hidden || link.user_hidden) // Unhide links that are selected
            .raise();

        nodes.filter(d => d.selected)
            .each(function(d) { //d.fixed |= 2;
                d.fx = d.x;
                d.fy = d.y;
            });

        //d.fixed = true;
        d3v4.select(this).classed("fixed", d.fixed = true);
    }

    function dragged(d) {
      //d.fx = d3v4.event.x;
      //d.fy = d3v4.event.y;
      nodes.filter(function(d) { return d.selected; })
      .each(function(d) {
          d.fx += d3v4.event.dx;
          d.fy += d3v4.event.dy;
      })
  }

  function dragended(d) {
      if (!d3v4.event.active) simulation.alphaTarget(0);
      //d.fx = null;
      //d.fy = null;
      nodes.filter(function(d) { return d.selected; })
      .each(function(d) { //d.fixed &= ~6;
          //d.fx = null;
          //d.fy = null;
      })
      links.filter(function(link) { return link.source.name == d.name || link.target.name == d.name; })
      .each(function(link) { return link.selected = false; })
  }

    function node_double_clicked(node) {
        node.fx = null;
        node.fy = null;
        d3v4.select(this).classed("fixed", node.fixed = false);
    }

    function _updateRadii() {
        const max_radius = params.max_radius;
        const min_radius = params.min_radius;
        const alpha = params.radius_decay;

        for (let node of graph.nodes) {
            node.radius = min_radius; // set a radius in case things go wrong
            let shortest_path = node.shortest_path;

            // Make the radius for the source band a little bigger
            if (shortest_path.length == 0) {
                node.radius = 1.25*max_radius;
                continue;
            }

            if (shortest_path.length == 1) {
                console.error('shortest path is length 1...');
                continue;
            }

            // Compute some sort of combined recommendation score
            // We want something that takes into account distance from the source
            let scores = []
            for (let i=1; i<shortest_path.length; ++i) {
                let key = [shortest_path[i-1], shortest_path[i]].join(',')
                let weight = link_map.get(key).sim_score;
                let degree = node_map.get(shortest_path[i-1]).degree;
                let score = weight / degree * alpha ** (i-1);
                scores.push(score)
            }

            // compute the geometric mean of the scores
            let score = scores.map(score => Math.log(score))
                              .reduce((x,y) => x+y, 0.);
            score = Math.exp(score / scores.length);
            node.radius_score = score;
        }

        // Now that we have all the scores, figure out radius and force_radial_factor
        // Normalize scores to be in [0,1].
        let scores = [];
        for (let node of graph.nodes) {
            if (!isNaN(node.radius_score)) {
                scores.push(node.radius_score);
            }
        }
        const max_score = Math.max(...scores);
        const min_score = Math.min(...scores);
        //console.log('max/min score', max_score, min_score);
        if (max_score == min_score) {
            throw "max_score == min_score... something's wrong";
        }

        radius_scores_sorted = scores.sort(); // sort scores and save a ref; we'll use it later for the quantile thing

        graph.nodes.forEach(function(node) {
            if (isNaN(node.radius_score)) {
                return;
            }
            node.radius_score = (node.radius_score - min_score) / (max_score - min_score);
        })

        // Now that we have all the scores, figure out radius and force_radial_factor
        for (let node of graph.nodes) {
            let score = node.radius_score;
            if (isNaN(score)) {
                node.force_radial_factor = 0;
                continue;
            }
            node.radius = min_radius + (max_radius - min_radius) * score;

            let factor = Math.max(0.05, (1. - score));
            //factor = Math.sqrt(factor);
            node.force_radial_factor = factor;
        }
    }

    function updateRadii() {
        _updateRadii()

        // Adjust the node radii
        gDraw.selectAll("circle")
             .attr("r", node => node.radius);

        // And the forceY simulation force depends on the radius
        simulation
            .force("y")
            .strength(function(node) {
                let factor = node.force_radial_factor;
                factor = factor ** 2;
                // rescale from [0,1] to [0.2, 0.5] or something
                min_scale = 0.2
                max_scale = 0.7
                factor = min_scale + (max_scale - min_scale)*factor
                return factor;
            })
        //simulation.force("radial")
        //    .radius(function(node) {
        //        let factor = node.force_radial_factor;
        //        return factor * 300;
        //    })

        // And also the text labels
        nodes_text.attr("x", node => node.radius+2)
    }

    function updateLinks() {
        const link_quantile = this.params.link_quantile;
        const link_quantile_method = this.params.link_quantile_method;

        //TODO this doesn't actually use a quantile!
        //     use Array.sort() and d3.quantile()
        if (link_quantile_method == 'score_threshold') {
            const min_sim_score = this.graph.min_sim_score;
            const max_sim_score = this.graph.max_sim_score;
            //var threshold = min_sim_score + (max_sim_score - min_sim_score)*link_quantile;
            const threshold_score = d3v4.quantile(sim_scores_sorted, link_quantile)
            var threshold = min_sim_score + (max_sim_score - min_sim_score)*threshold_score;

            var node_test = function(node) {
                throw "not implemented";
            }

            var link_test = function(link) {
                return link.sim_score < threshold;
            };

        } else if (link_quantile_method == 'radius_threshold') {
            const min_radius = this.params.min_radius;
            const max_radius = this.params.max_radius;
            //var threshold = min_radius + (max_radius - min_radius)*link_quantile;
            const threshold_score = d3v4.quantile(radius_scores_sorted, link_quantile)
            var threshold = min_radius + (max_radius - min_radius)*threshold_score;

            var node_test = function(node) {
                return node.radius < threshold;
            }

            var link_test = function(link) {
                source = link.source;
                target = link.target;
                //radius = Math.max(source.radius, target.radius);
                radius = Math.min(source.radius, target.radius)
                //radius = 0.5*(source.radius + target.radius)
                //threshold = min_radius + (max_radius - min_radius)*link_quantile;
                return radius < threshold;
            };

        } else {
            throw Error('bad updateLinks method')
        }

        this.nodes
            .each(function(node) {
                hidden = false;
                if (!node.selected && node_test(node)) {
                    hidden = true;
                }
                node.hidden = hidden;
            })
            .classed("hidden", node => node.hidden)

        this.links
            .each(function(link) {
                hidden = false;
                if (!link.source.selected && link_test(link)) {
                    hidden = true;
                }
                link.hidden = hidden;
            })
            .classed("hidden", link => link.hidden || link.user_hidden)

        this.nodes_text
            .each(function(text) {
                hidden = false;
                if (!text.selected && node_test(text)) {
                    hidden = true;
                }
                text.hidden = hidden;
            })
            .classed("hidden", text => text.hidden)

        // Filter nodes, links, texts based on hidden state
        let new_nodes = this.graph.nodes.filter(node => !node.hidden);
        let new_links = this.graph.links.filter(link => !(link.hidden || link.user_hidden))

        // Apply the general update pattern to the nodes.
        nodes = nodes.data(new_nodes, function(d) { return d.id;});
        nodes.exit().remove();
        nodes = nodes.enter().append("circle").attr("r", d => d.radius).merge(nodes);

        // Apply the general update pattern to the links.
        links = links.data(new_links, function(d) { return d.source.id + "-" + d.target.id; });
        links.exit().remove();
        links = links.enter().append("line").merge(links);

        // Apply the general update pattern to the nodes_text.
        nodes_text = nodes_text.data(new_nodes, function(d) { return d.id;});
        nodes_text.exit().remove();
        nodes_text = nodes_text.enter().append("circle").attr("r", d => d.radius).merge(nodes_text);

        // Update and restart the simulation.
        simulation.nodes(new_nodes)
        simulation.force("link").links(new_links);
        simulation.alpha(1).restart();
    }

    // hide/un-hide a node's links on right click
    svg.on("contextmenu", function() {
        d3v4.event.preventDefault();
    })

    nodes.on("contextmenu", function(node) {
        d3v4.event.preventDefault();
        links.filter(link => link.source.name == node.name || link.target.name == node.name)
            .each(function (link) {
                //link.selected = false;
                link.user_hidden = !link.user_hidden;
            })
            //.classed("selected", link => link.selected)
            .classed("hidden", link => link.user_hidden)
    })

    // un-hide nodes hidden by link.user_hidden
    function unhide_links() {
        links.each(link => link.user_hidden = false)
            .classed("hidden", link => link.hidden || link.user_hidden)
    }

    function hide_links() {
        links.each(link => link.user_hidden = true)
            .filter(link => !link.selected)
            .classed("hidden", link => link.hidden || link.user_hidden)
    }

    // free any fixed nodes
    function free_fixed_nodes() {
        nodes.each(node => node.fixed = false)
            .classed("fixed", false)
    }

    function startSimulation() {
        simulation.restart();
    }

    function stopSimulation() {
        simulation.stop();
    }

    //var texts = ['Use the scroll wheel to zoom',
    //             ]
//
    //svg.selectAll('text')
    //    .data(texts)
    //    .enter()
    //    .append('text')
    //    .attr('x', 900)
    //    .attr('y', function(d,i) { return 470 + i * 18; })
    //    .text(function(d) { return d; });

    return {graph: graph,
            links: links,
            nodes: nodes,
            nodes_text: nodes_text,
            params: params,
            startSimulation: startSimulation,
            stopSimulation: stopSimulation,
            updateRadii: updateRadii,
            updateLinks: updateLinks,
            unhideLinks: unhide_links,
            hideLinks: hide_links,
            freeFixedNodes: free_fixed_nodes,
            }
};
