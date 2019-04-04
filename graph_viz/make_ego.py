import json, argparse
import sqlite3 as lite

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

class EgoGraphs(object):
    def __init__(self, database="../database.db"):
        self.database = str(database)
        self.readDatabase()
        self.makeGraph()

    def readDatabase(self):
        with lite.connect(f'file:{database}?mode=ro', uri=True) as con:
            cur = con.cursor()

            #cur.execute('select band_id from Bands where band=?', (band_name,))
            #resp = cur.fetchone()
            #if len(resp) != 1:
            #    raise RuntimeError("didn't find that band")
            #band_id = str(resp[0])

            #cur.execute('select count(*) from Reviews where band_id=?', (band_id,))
            #resp = cur.fetchone()
            #if len(resp) != 1:
            #    num_reviews = 0
            #else:
            #    num_reviews = int(resp[0])

            cur.execute('select band_id,band from Bands where band_id in (select band_id from Similarities)')
            self.bands_list = cur.fetchall()

            cur.execute('select band_id,similar_to_id,score from Similarities where similar_to_id in (select band_id from Similarities)')
            self.sim_list = cur.fetchall()

        self.band_id_to_band = {band_id:band for band_id,band in self.bands_list}
        #self.band_to_band_id = {band:band_id for band_id,band in self.bands_list}

        #self.node_list = list(set(band_id for band_id,_,_ self.sim_list))
        self.edge_list = [(band_id,similar_to_id,score) for band_id,similar_to_id,score in self.sim_list]

    def makeGraph(self):
        G = nx.Graph()
        G.add_weighted_edges_from(self.edge_list)
        self.G = nx.relabel_nodes(G, self.band_id_to_band)

    def makeEgoGraph(self, band_name, ego_radius=2):
        # https://stackoverflow.com/questions/17301887/how-to-compute-nearby-nodes-with-networkx
        ego = nx.ego_graph(self.G, band_name, radius=ego_radius, center=True)

        self.setNodeRadii(ego, band_name)
        self.setEdgeStrokeWidth(ego, band_name)

        return ego

    def setNodeRadii(self, ego, band_name, method='shortest_path'):
        """
        Set each node's 'radius' property
        """
        min_radius = 3
        max_radius = 10

        if method == 'linear_indeg':
            # radius is proportional to degree.  This will show popular bands
            nodes = ego.nodes()
            indegs = ego.degree(nodes, weight='weight')
            min_indeg = min(t[1] for t in indegs)
            max_indeg = max(t[1] for t in indegs)

            for node, indeg_tuple in zip(nodes, indegs):
                indeg = indeg_tuple[1]
                radius = float(indeg - min_indeg) / float(max(1, max_indeg - min_indeg)) # in [0,1]
                radius = min_radius + (max_radius-min_radius)*radius # in [min_radius, max_radius]

                ego.node[node]['radius'] = radius

        elif method == 'shortest_path':
            # Compute inverse of weight == inverse of recommendation score
            for edge in ego.edges():
                ego.edges[edge]['invweight'] = 1./ego.edges[edge]['weight']

            # Compute shortest paths from band to all other nodes based on 'invweight'
            length_dict, path_dict = nx.single_source_dijkstra(ego, band_name, weight='invweight')

            # Set each node to min_radius, in case the shortest path thing below craps out
            # This shouldn't happen if ego is actually an ego graph
            for node in ego.nodes():
                ego.nodes[node]['radius'] = min_radius

            # Set requested band to max_radius plus a little bit
            ego.nodes[band_name]['radius'] = 1.25*max_radius

            for target, path in path_dict.items():
                if not path:
                    print('missing a path')
                    continue

                if len(path) == 1: # path length 0 is band_name to band_name
                    continue

                # Compute some sort of combined recommendation score
                # Want something that takes into account distance from source (band_name)
                # score = 1/1*neighbor_band + 1/2*neighbor_or_neighbor?
                # Geometric mean?
                #weights = [ego.edges[(path[i-1],path[i])]['weight'] for i in range(1,len(path))]
                alpha = 0.1; # penalty for being farther from the source
                #weights = [ego.edges[(path[i-1],path[i])]['weight']*alpha**(i-1) for i in range(1,len(path))]
                weights = [ego.edges[(path[i-1],path[i])]['weight']/ego.degree(path[i-1])*alpha**(i-1) for i in range(1,len(path))]
                score = np.exp(np.sum(np.log(weights))/len(weights))
                #score /= len(weights)

                ego.nodes[target]['score'] = score

                # Also store the path from band_name to this node
                ego.nodes[target]['path'] = path

            #scores = [t[1]['score'] for t in ego.nodes(data=True) if 'score' in t[1]]
            #plt.figure()
            #plt.hist(scores, bins=25)
            #plt.show()

            # Take only the upper qth quantile of the scores, to trim the graph a bit
            # Or better yet, specify a max size?
            scores = [t[1]['score'] for t in ego.nodes(data=True) if 'score' in t[1]]
            #limit = np.quantile(scores, 0.5)
            max_size = 250
            ind = max(0, len(ego) - max_size)
            limit = np.partition(scores, ind)[ind]
            nodes = list(ego.nodes(data=True))
            for t in nodes:
                if 'score' not in t[1]:
                    continue

                score = t[1]['score']
                if score < limit:
                    ego.remove_node(t[0])

            # And if any nodes are isolated, drop them
            nodes = list(ego.nodes(data=True))
            for t in nodes:
                if ego.degree(t[0]) == 0:
                    ego.remove_node(t[0])

            print(len(ego))

            min_score = min(t[1]['score'] for t in ego.nodes(data=True) if 'score' in t[1])
            max_score = max(t[1]['score'] for t in ego.nodes(data=True) if 'score' in t[1])
            print(min_score, max_score)
            for node,data in ego.nodes(data=True):
                if 'score' not in data:
                    continue

                score = data['score']
                score = float(score - min_score) / float(max(1, max_score - min_score))
                score = score
                radius = min_radius + (max_radius - min_radius)*score
                ego.nodes[node]['radius'] = radius

            # Scale factor for forceRadial
            for node in ego.nodes():
                radius = ego.nodes[node]['radius']
                factor = max(0, 1. - float(radius - min_radius) / float(max(1, max_radius - min_radius)))
                factor = factor ** 2
                ego.nodes[node]['force_radial_factor'] = factor

        else:
            raise ValueError('Dunno that method')

    def setEdgeStrokeWidth(self, ego, band_name, method='weight_simple'):
        """
        Set each edge's 'stroke_width' property
        """
        if method == 'weight_simple':
            # stroke width is simply the score... doesn't show relation to requested band
            min_weight = min(t[2]['weight'] for t in ego.edges(data=True))
            max_weight = max(t[2]['weight'] for t in ego.edges(data=True))

            for t in ego.edges(data=True):
                source, target, data = t
                weight = data['weight']

                width = weight
                width = float(width - min_weight) / float(max(1, max_weight - min_weight))
                width = width ** 0.33
                #width = np.log10(width+1)

                min_width = 1.5
                max_width = 4
                width = min_width + (max_width - min_width) * width
                #print(width)

                ego.edges[(source,target)]['stroke_width'] = width

        else:
            raise ValueError('Dunno that method')

    def writeJSON(self, json_file, ego):
        nodes = [{'name': str(t[0]),
                  'radius': t[1]['radius'],
                  'force_radial_factor': t[1]['force_radial_factor'],
                  'path': t[1].get('path', []),
                  }
                  for t in ego.nodes(data=True)]

        links = [{'source': t[0],
                  'target': t[1],
                  'stroke_width': t[2]['stroke_width'],
                  'sim_score': t[2]['weight'],
                  }
                  for t in ego.edges(data=True)]

        min_radius = min(t[1]['radius'] for t in ego.nodes(data=True))
        max_radius = max(t[1]['radius'] for t in ego.nodes(data=True))

        min_sim_score = min(v['sim_score'] for v in links)
        max_sim_score = max(v['sim_score'] for v in links)

        data = {'nodes': nodes,
                'links': links,
                'min_radius': min_radius,
                'max_radius': max_radius,
                'min_sim_score': min_sim_score,
                'max_sim_score': max_sim_score,
                }

        with open(json_file, 'w') as f:
            json.dump(data, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('json_out')
    parser.add_argument('band_name')

    args = parser.parse_args()

    database = "../database.db"
    ego_graphs = EgoGraphs(database)
    ego = ego_graphs.makeEgoGraph(args.band_name, ego_radius=2)
    ego_graphs.writeJSON(args.json_out, ego)

    #plt.figure()
    #nx.draw_spring(ego, with_labels=True)
    #plt.show()
