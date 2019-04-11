import json, os, pickle, time
#import base64, gzip
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

import boto3, botocore

from make_ego2 import EgoGraphs

def get_database(fn):
    if os.path.isfile(fn):
        logger.debug("Got database from local file %s", fn)
        return True

    bucket = 'jamesfolberth.org'
    object = 'data/metal-archives/similarity_database.db'

    s3 = boto3.resource('s3')

    _t = time.time()
    try:
        s3.Bucket(bucket).download_file(object, fn)
    except botocore.exceptions.ClientError as e:
        logger.exception(e)
        return False
    _t = time.time() - _t
    logger.info("Pulled database from S3 in %f seconds", _t)

    return True

def get_ego_graphs(ego_graphs_filename, database_filename):
    if os.path.isfile(ego_graphs_filename):
        logger.debug("Going to unpickle EgoGraphs from %s", ego_graphs_filename)
        _t = time.time()
        with open(ego_graphs_filename, 'rb') as f:
            ego_graphs = pickle.load(f)
        _t = time.time() - _t
        logger.info("Unpickling EgoGraphs took %f seconds", _t)
        return ego_graphs

    logger.debug("Going to make an EgoGraphs object")
    _t = time.time()
    ego_graphs = EgoGraphs()
    ego_graphs.readDatabase(database_filename)
    ego_graphs.makeGraph()
    _t = time.time() - _t
    logger.info("Making EgoGraphs took %f seconds", _t)

    logger.debug("Pickling EgoGraphs to %s", ego_graphs_filename)
    _t = time.time()
    with open(ego_graphs_filename, 'wb') as f:
        pickle.dump(ego_graphs, f)
    _t = time.time() - _t
    logger.info("Pickling EgoGraphs took %f seconds", _t)

    return ego_graphs

#def gzip_stuff(stuff):
#    _t = time.time()
#    stuff_bytes = bytes(stuff, 'utf-8')
#    stuff_gzip = gzip.compress(stuff_bytes, compresslevel=9)
#    stuff_b64 = base64.b64encode(stuff_gzip).decode('ascii')
#    _t = time.time() - _t
#    logger.debug("gzip JSON response took %f seconds", _t)
#    return stuff_b64

def lambda_handler(event, context):
    # Check that the request has a queryStringParameters: {'band_name': band_name}
    if 'queryStringParameters' not in event or 'band_name' not in event['queryStringParameters']:
        return {'statusCode': 400,
                'body': json.dumps("You must specify a 'band_name' query"),
                }

    band_name = str(event['queryStringParameters']['band_name'])
    logger.debug("Got band_name=%s", band_name)

    # Get the similarity database (possibly from /tmp cache)
    database_filename = '/tmp/sim.db'
    got_it = get_database(database_filename)
    if not got_it:
        return {'statusCode': 500,
                'body': json.dumps("Couldn't get similarity database from S3"),
                }

    # Create EgoGraph object (or get from /tmp cache)
    ego_graphs_filename = '/tmp/ego_graphs.pkl'
    ego_graphs = get_ego_graphs(ego_graphs_filename, database_filename)
    if not ego_graphs:
        return {'statusCode': 500,
                'body': json.dumps("Couldn't make an EgoGraphs object"),
                }

    # Compute the ego graph
    ego = ego_graphs.makeEgoGraph(band_name, ego_radius=2)
    ego_json = ego_graphs.makeResponse(ego)

    # Gzip the response
    # Actually, it looks like API Gateway can now do this for us.  Cool!

    return {'statusCode': 200,
            'body': ego_json
            }
