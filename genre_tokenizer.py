
import argparse, json
import sqlite3 as lite
from pprint import pprint
import logging
logger = logging.getLogger(__name__)

import tqdm

from utils import *
from genreTokenizer import GenreTokenizer

def main(database, method='bag-of-words'):
    with lite.connect(database) as connection:
        cursor = connection.cursor()
        
        n_do = cursor.execute('select count(band_id) from Bands').fetchall()[0][0]
        logger.info('Going to tokenize %d genre texts', n_do)
        
        tokenizer = GenreTokenizer(method=method)
        genre_cursor = connection.cursor()
        for band_id,genre in tqdm.tqdm(genre_cursor.execute('select band_id,genre from Bands'), total=n_do):
            logger.debug('band_id = %d, genre = %s', band_id, genre)
            
            tokens = tokenizer.tokenize(genre)
            tokens_str = json.dumps(tokens)
            logger.debug('tokens = %s', tokens_str)
            
            cursor.execute('update Bands set genre_tokens=? where band_id=?',
                           (tokens_str, band_id))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tokenize the genre text for each '
                                     'band in the database.  This updates the '
                                     '`genre_tokens` column.')
    parser.add_argument('database', type=str,
                        help='Filename of sqlite3 database; must already exist')
    
    parser.add_argument('--method', type=str, default='bag-of-words',
                        help='Tokenization method: "bagOfWords", "split2"')
    
    #subparsers?
    parser.add_argument('--logging-level', type=int, default=logging.WARNING,
                        help="Set the logging level")
    
    args = parser.parse_args()
    
    logging.basicConfig(stream=tqdmForLogging, level=args.logging_level)
    
    main(args.database, method=args.method)
