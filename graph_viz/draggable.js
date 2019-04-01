
var graphProperties = {
    review_quantile: 0,
}


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

    var nodes = {};
    var i;
    for (i = 0; i < graph.nodes.length; i++) {
        nodes[graph.nodes[i].name] = graph.nodes[i];
        //graph.nodes[i].weight = 1.01;
    }

    // the brush needs to go before the nodes so that it doesn't
    // get called when the mouse is over a node
    //var gBrushHolder = gDraw.append('g');
    //var gBrush = null;

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

    var simulation = d3v4.forceSimulation()
        .force("link", d3v4.forceLink()
                .id(function(d) { return d.name; })
                //.distance(50)
                //.strength(0)
              )
        .force("charge", d3v4.forceManyBody()
                //.strength(-50)
                //.strength(node => Math.min(-20, Math.max(-30, -20./Math.sqrt(node.radius))))
                .distanceMin(20)
                //.distanceMax(200)
            )
        //.force("collide", d3v4.forceCollide()
        //        .radius(20))
        .force("center", d3v4.forceCenter(parentWidth / 2, parentHeight / 2))
        //.force("x", d3v4.forceX(parentWidth/2))
        //.force("y", d3v4.forceY(parentHeight/2))
        .force("y", d3v4.forceY(parentHeight)
                .strength(function(node) {
                    factor = node.force_radial_factor;
                    factor = Math.sqrt(factor);
                    // rescale from [0,1] to [0.2, 0.5]
                    min_scale = 0.1
                    max_scale = 0.4
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

    //var brushMode = false;
    //var brushing = false;

    //var brush = d3v4.brush()
    //    .on("start", brushstarted)
    //    .on("brush", brushed)
    //    .on("end", brushended);

    //function brushstarted() {
    //    // keep track of whether we're actively brushing so that we
    //    // don't remove the brush on keyup in the middle of a selection
    //    brushing = true;
//
    //    node.each(function(d) {
    //        d.previouslySelected = shiftKey && d.selected;
    //    });
    //}

    rect.on('click', () => {
        //node.each(function(d) {
        //    d.selected = false;
        //    //d.previouslySelected = false;
        //});
        node.classed("selected", false);
        //link.each(function(link) { link.selected = false; });
        link.classed("selected", false);
    });

    //function brushed() {
    //    if (!d3v4.event.sourceEvent) return;
    //    if (!d3v4.event.selection) return;
//
    //    var extent = d3v4.event.selection;
//
    //    node.classed("selected", function(d) {
    //        return d.selected = d.previouslySelected ^
    //        (extent[0][0] <= d.x && d.x < extent[1][0]
    //         && extent[0][1] <= d.y && d.y < extent[1][1]);
    //    });
    //}

    //function brushended() {
    //    if (!d3v4.event.sourceEvent) return;
    //    if (!d3v4.event.selection) return;
    //    if (!gBrush) return;
//
    //    gBrush.call(brush.move, null);
//
    //    if (!brushMode) {
    //        // the shift key has been release before we ended our brushing
    //        gBrush.remove();
    //        gBrush = null;
    //    }
//
    //    brushing = false;
    //}

    //d3v4.select('body').on('keydown', keydown);
    //d3v4.select('body').on('keyup', keyup);
//
    //var shiftKey;
//
    //function keydown() {
    //    shiftKey = d3v4.event.shiftKey;
//
    //    if (shiftKey) {
    //        // if we already have a brush, don't do anything
    //        if (gBrush)
    //            return;
//
    //        brushMode = true;
//
    //        if (!gBrush) {
    //            gBrush = gBrushHolder.append('g');
    //            gBrush.call(brush);
    //        }
    //    }
    //}
//
    //function keyup() {
    //    shiftKey = false;
    //    brushMode = false;
//
    //    if (!gBrush)
    //        return;
//
    //    if (!brushing) {
    //        // only remove the brush if we're not actively brushing
    //        // otherwise it'll be removed when the brushing ends
    //        gBrush.remove();
    //        gBrush = null;
    //    }
    //}

    function dragstarted(d) {
        if (!d3v4.event.active) simulation.alphaTarget(0.9).restart();

        if (!d.selected) {
            // if this node isn't selected, then we have to unselect every other node
            node.classed("selected", function(p) {
                p.selected = false;
                return false;
            });
        }

        // Set links that source from this node to selected
        link.filter((link) => link.source.name == d.name)
            .each((link) => link.selected = true )

        // Set the selected class for this node and links
        d3v4.select(this).classed("selected", (d) => d.selected = true);

        // Unselect the other links
        link.filter((link) => link.source.name != d.name)
            .classed("selected", false)

        link.filter((d) => d.selected)
            .classed("selected", (d) => d.selected)
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
        link.filter(function(link) { return link.source.name == d.name; })
            .each(function(link) { return link.selected = false; })
    }

    function node_double_clicked(node) {
        node.fx = null;
        node.fy = null;
        d3v4.select(this).classed("fixed", node.fixed = false);
    }

    function updateLinks() {
        const min_review_score = this.graph.min_review_score;
        const max_review_score = this.graph.max_review_score;

        this.link
            .each(function(link) {
            hidden = false;
            threshold = min_review_score + (max_review_score - min_review_score)*graphProperties.review_quantile;
            if (link.review_score < threshold) {
                hidden = true;
            }
            link.hidden = hidden;
        })
        .classed("hidden", link => link.hidden)
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
            }
};
