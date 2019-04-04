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
        link_quantile: 0.,
    };

    var nodes = {};
    var i;
    for (i = 0; i < graph.nodes.length; i++) {
        nodes[graph.nodes[i].name] = graph.nodes[i];
    }

    var link = gDraw.append("g")
        .attr("class", "link")
        .selectAll("line")
        .data(graph.links)
        .enter().append("line")
        .attr("stroke-width", d => d.stroke_width );

    var node = gDraw.append("g")
        .attr("class", "node")
        .selectAll("circle")
        .data(graph.nodes)
        .enter().append("circle")
        .attr("r", d => d.radius)
        //.attr("fill", function(d) {
        //    if ('color' in d)
        //        return d.color;
        //    else
        //        return color(d.group);
        //})
        .on("dblclick", node_double_clicked)
        .call(d3v4.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // initialize properties we'll use for interaction with the nodes & links
    node.each(function(node) {
        node.selected = false;
        node.hidden = false;
        node.fixed = false;
        })

    link.each(function(link) {
        link.hidden = false;
        link.user_hidden = false;
        })

    // add titles for mouseover blurbs
    //node.append("title")
    //    .text(function(d) {
    //        if ('name' in d)
    //            return d.name;
    //        else
    //            return d.id;
    //    });
    var labels = node.append("text")
        .text(d => d.name)
        .attr('x', 6)
        .attr('y', 3);

    node.append("title")
        .text(d => d.name);

    link.append("title")
        .text(function(link) {
            s = link.source + ' similar to ';
            s += link.target + ' with ' + link.sim_score + ' votes';
            return s;
        })

    var simulation = d3v4.forceSimulation()
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
        //        .radius(20))
        .force("center", d3v4.forceCenter(0.5*parentWidth, 0.7*parentHeight))
        .force("x", d3v4.forceX(0.5*parentWidth).strength(0.05))
        .force("y", d3v4.forceY(parentHeight)
                .strength(function(node) {
                    factor = node.force_radial_factor;
                    factor = Math.sqrt(factor);
                    // rescale from [0,1] to [0.2, 0.5] or something
                    min_scale = 0.2
                    max_scale = 0.7
                    factor = min_scale + (max_scale - min_scale)*factor
                    return factor;
                }))
        //.force("radial", d3v4.forceRadial()
        //    .radius(node => 500*Math.max(0, 1-(node.radius-3)/(10-3))**2)
        //    .x(parentWidth/2)
        //    .y(parentHeight/2)
        //    .strength(function(node) { return 0.1; }))
        //;

    simulation
        .nodes(graph.nodes)
        .on("tick", ticked);

    simulation.force("link")
        .links(graph.links);

    function ticked() {
        // update node and line positions at every step of
        // the force simulation
        link.attr("x1", function(d) { return d.source.x; })
            .attr("y1", function(d) { return d.source.y; })
            .attr("x2", function(d) { return d.target.x; })
            .attr("y2", function(d) { return d.target.y; });

        node.attr("cx", function(d) { return d.x; })
            .attr("cy", function(d) { return d.y; });
    }

    rect.on('click', () => {
        node.each(node => node.selected = false)
            .classed("selected", false);
        link.each(link => link.selected = false)
            .classed("selected", false);
    });

    function dragstarted(d) {
        if (!d3v4.event.active) simulation.alphaTarget(0.9).restart();

        if (!d.selected) {
            // if this node isn't selected, then we have to unselect every other node
            node.classed("selected", function(node) {
                node.selected = false;
                return false;
            });
        }

        // Set links that source from this node to selected
        link.filter((link) => link.source.name == d.name || link.target.name == d.name)
            .each(function(link) {
                link.selected = true;
                link.hidden = false;
                link.user_hidden = false;
            })

        // Set the selected class for this node and links
        d3v4.select(this).classed("selected", (d) => d.selected = true);

        // Unselect the other links
        link.filter((link) => link.source.name != d.name && link.target.name != d.name)
            .classed("selected", false)

        link.filter((link) => link.selected)
            .classed("selected", true)
            .classed("hidden", link => link.hidden || link.user_hidden) // Unhide links that are selected
            .raise();

        node.filter(d => d.selected)
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
      node.filter(function(d) { return d.selected; })
      .each(function(d) {
          d.fx += d3v4.event.dx;
          d.fy += d3v4.event.dy;
      })
  }

  function dragended(d) {
      if (!d3v4.event.active) simulation.alphaTarget(0);
      //d.fx = null;
      //d.fy = null;
      node.filter(function(d) { return d.selected; })
      .each(function(d) { //d.fixed &= ~6;
          //d.fx = null;
          //d.fy = null;
      })
      link.filter(function(link) { return link.source.name == d.name || link.target.name == d.name; })
      .each(function(link) { return link.selected = false; })
  }

    function node_double_clicked(node) {
        node.fx = null;
        node.fy = null;
        d3v4.select(this).classed("fixed", node.fixed = false);
    }

    function updateLinks() {
        const link_quantile = this.params.link_quantile;
        const link_quantile_method = this.params.link_quantile_method;

        if (link_quantile_method == 'score_threshold') {
            const min_sim_score = this.graph.min_sim_score;
            const max_sim_score = this.graph.max_sim_score;

            var threshold_test = function(link) {
                threshold = min_sim_score + (max_sim_score - min_sim_score)*link_quantile;
                return link.sim_score < threshold;
            };

        } else if (link_quantile_method == 'radius_threshold') {
            const min_radius = this.graph.min_radius;
            const max_radius = this.graph.max_radius;

            var threshold_test = function(link) {
                source = link.source
                target = link.target
                //radius = Math.max(source.radius, target.radius)
                //radius = Math.min(source.radius, target.radius)
                radius = 0.5*(source.radius + target.radius)
                threshold = min_radius + (max_radius - min_radius)*link_quantile;
                return radius < threshold;
            };

        } else {
            throw Error('bad updateLinks method')
        }

        this.link
            .each(function(link) {
                hidden = false;
                if (!link.source.selected && threshold_test(link)) {
                    hidden = true;
                }
                link.hidden = hidden;
            })
            .classed("hidden", link => link.hidden || link.user_hidden)
    }

    // hide/un-hide a node's links on right click
    svg.on("contextmenu", function() {
        d3v4.event.preventDefault();
    })

    node.on("contextmenu", function(node) {
        d3v4.event.preventDefault();
        link.filter(link => link.source.name == node.name || link.target.name == node.name)
            .each(function (link) {
                //link.selected = false;
                link.user_hidden = !link.user_hidden;
            })
            //.classed("selected", link => link.selected)
            .classed("hidden", link => link.user_hidden)
    })

    // un-hide nodes hidden by link.user_hidden
    function unhide_links() {
        link.each(link => link.user_hidden = false)
            .classed("hidden", link => link.hidden || link.user_hidden)
    }

    function hide_links() {
        link.each(link => link.user_hidden = true)
            .filter(link => !link.selected)
            .classed("hidden", link => link.hidden || link.user_hidden)
    }

    // free any fixed nodes
    function free_fixed_nodes() {
        node.each(node => node.fixed = false)
            .classed("fixed", false)
    }

    var texts = ['Use the scroll wheel to zoom',
                 ]

    svg.selectAll('text')
        .data(texts)
        .enter()
        .append('text')
        .attr('x', 900)
        .attr('y', function(d,i) { return 470 + i * 18; })
        .text(function(d) { return d; });

    return {graph: graph,
            link: link,
            node: node,
            updateLinks: updateLinks,
            unhideLinks: unhide_links,
            hideLinks: hide_links,
            freeFixedNodes: free_fixed_nodes,
            params: params,
            }
};
