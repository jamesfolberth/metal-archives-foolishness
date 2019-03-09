import csv
import logging
logger = logging.getLogger(__name__)

import tqdm

__all__ = ['get_band_id_from_band_url',
           'get_album_id_from_album_url',
           'get_user_id_from_review_url',
           'read_csv_to_list_of_dicts',
           'flatten',
           'tqdmForLogging',
           ]

def get_band_id_from_band_url(band_url):
    # IDs are positive integers, so we can use str.isdigit()
    band_id = band_url.split('/')[-1]
    if not band_id.isdigit():
        return None
    else:
        return int(band_id)

def get_album_id_from_album_url(album_url):
    return get_band_id_from_band_url(album_url)

def get_user_id_from_review_url(review_url):
    return get_band_id_from_band_url(review_url)

def read_csv_to_list_of_dicts(csv_filename):
    with open(csv_filename, 'r') as f:
        reader = csv.DictReader(f)
        csv_list = [row for row in reader]
    return csv_list

def flatten(iterable):
    """
    Flaten out a list of lists.  For example
    [['a','b'], ['c']] -> ['a', 'b', 'c']
    """
    return [item for subiterable in iterable for item in subiterable]

# This dude exists only to specify end="" instead of end="\n"
# TODO: There's got to be a better way... somelike like functools.partialmethod?
#       Or make a logging.StreamHandler
class tqdmForLogging(tqdm.tqdm):
    @classmethod
    def write(cls, s, file=None, end="", nolock=False):
        super().write(s, file, end, nolock)
        
        
