"""
Like make_ego.py, but puts more stuff in the JS and is used by AWS Lambda stuff
"""
import json, time
import sqlite3 as lite
import logging
logger = logging.getLogger()

import networkx as nx

class EgoGraphs(object):
    def __init__(self):
        pass

    def readDatabase(self, database):
        _t = time.time()
        with lite.connect(f'file:{database}?mode=ro', uri=True) as con:
            cur = con.cursor()

            cur.execute('select band_id,band,band_url from Bands where band_id in (select band_id from Similarities)')
            self.bands_list = cur.fetchall()

            cur.execute('select band_id,similar_to_id,score from Similarities where similar_to_id in (select band_id from Similarities)')
            self.sim_list = cur.fetchall()
        _t = time.time() - _t
        logger.info("Fetching from database took %f seconds", _t)

        self.band_id_to_band = {band_id:band for band_id,band,_ in self.bands_list}
        self.band_to_band_id = {band:band_id for band_id,band,_ in self.bands_list}
        self.band_id_to_band_url = {band_id:band_url for band_id,_,band_url in self.bands_list}

        #self.node_list = list(set(band_id for band_id,_,_ self.sim_list))
        self.edge_list = [(band_id,similar_to_id,score) for band_id,similar_to_id,score in self.sim_list]

    def makeGraph(self):
        _t = time.time()
        G = nx.Graph()
        G.add_weighted_edges_from(self.edge_list)
        #self.G = nx.relabel_nodes(G, self.band_id_to_band)
        self.G = G
        _t = time.time() - _t
        logger.info("Creating nx.Graph took took %f seconds", _t)

        del self.bands_list
        del self.sim_list
        #del self.band_id_to_band
        del self.edge_list

    def makeEgoGraph(self, band_name, ego_radius=2):
        _t = time.time()
        band_id = self.band_to_band_id[band_name]
        ego = nx.ego_graph(self.G, band_id, radius=ego_radius, center=True)

        self.setShortestPathTo(ego, band_id)
        _t = time.time() - _t
        logger.info("Making ego graph with shortest paths took %f seconds", _t)

        return ego

    def setShortestPathTo(self, ego, band_id):
        """
        Compute the shortest path (based on inverse similarity score) from
        each node to band_name.  The JS stuff will use this to compute each
        node's radius.
        """
        # Compute inverse of weight == inverse of recommendation score
        for edge in ego.edges():
            ego.edges[edge]['invweight'] = 1./ego.edges[edge]['weight']

        # Compute shortest paths from band to all other nodes based on 'invweight'
        length_dict, path_dict = nx.single_source_dijkstra(ego, band_id, weight='invweight')

        for target, path in path_dict.items():
            if not path:
                print('missing a path')
                continue

            if len(path) == 1: # path length 0 is band_id to band_id
                continue

            end_node = path[-1]
            ego.nodes[end_node]['shortest_path'] = path

    def makeResponse(self, ego):
        band_name = lambda band_id: self.band_id_to_band[band_id]

        nodes = [{'name': str(band_name(t[0])),
                  'shortest_path': list(map(band_name, t[1].get('shortest_path', []))),
                  'degree': ego.degree(t[0]),
                  'band_url': self.band_id_to_band_url[t[0]],
                  }
                  for t in ego.nodes(data=True)]

        links = [{'source': band_name(t[0]),
                  'target': band_name(t[1]),
                  'sim_score': t[2]['weight'],
                  }
                  for t in ego.edges(data=True)]

        min_sim_score = min(v['sim_score'] for v in links)
        max_sim_score = max(v['sim_score'] for v in links)

        data = {'nodes': nodes,
                'links': links,
                'min_sim_score': min_sim_score,
                'max_sim_score': max_sim_score,
                }

        return json.dumps(data)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('json_out')
    parser.add_argument('band_name')

    args = parser.parse_args()

    #database = "../database.db"
    database = "../similarity_database.db"
    ego_graphs = EgoGraphs()
    ego_graphs.readDatabase(database)
    ego_graphs.makeGraph()
    ego = ego_graphs.makeEgoGraph(args.band_name, ego_radius=2)
    with open(args.json_out, 'w') as f:
        f.write(ego_graphs.makeResponse(ego))

    #plt.figure()
    #nx.draw_spring(ego, with_labels=True)
    #plt.show()
