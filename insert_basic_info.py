import argparse, datetime, os, csv
import sqlite3 as lite
from pprint import pprint
import logging
logger = logging.getLogger(__name__)

import tqdm

from utils import *

class InsertBasicInfo(object):
    """
    Inserts basic info from band and review CSVs into database.
    """
    def __init__(self, database_filename):
        """
        Params:
            database_filename - name of sqlite3 database file
        """
        
        if not os.path.isfile(database_filename):
            raise ValueError("Database file {} doesn't exist".format(database_filename))
        self.database_filename = database_filename
    
    def run(self, band_list_filename, review_list_filename):
        bands_list = read_csv_to_list_of_dicts(band_list_filename)
        with lite.connect(self.database_filename) as self.connection:
            logger.info('Adding basic band info')
            for band_info in tqdm.tqdm(bands_list):
                self.insertBasicBandInfo(band_info)
        
        reviews_list = read_csv_to_list_of_dicts(review_list_filename) 
        with lite.connect(self.database_filename) as self.connection:
            logger.info('Adding basic review/album/reviewer info')
            for review_info in tqdm.tqdm(reviews_list):
                self.insertBasicReviewInfo(review_info)
            
    def insertBasicBandInfo(self, band_info):
        """
        Inserts basic band info into the Bands table.
        """
        band_url = band_info['band_url']
        band = band_info['band']
        country = band_info['country']
        genre = band_info['genre']
        status = band_info['status']
        
        band_id = get_band_id_from_band_url(band_url)
        if band_id is None:
            logger.warning("Skipping band %s, since we can't produce a valid band_id from %s", band, band_info)
            return
        
        cur = self.connection.cursor()
        
        # check if band is already in the DB
        cur.execute('select band_id from Bands where band_id = ?', (band_id,))
        rows = cur.fetchall()
        
        if len(rows) > 1:
            raise RuntimeError("More than one band_id matches query.  That's a bug.")
        
        elif len(rows) == 1:
            logger.debug('Band %s with id %d already in Bands; updating basic info', band, band_id)
            cur.execute('update Bands ' + 
                        "set band=?, band_url=?,country=?,genre=?,status=?,insert_date=datetime('now') " +
                        'where band_id=?',
                        (band,band_url,country,genre,status,band_id))
            
        else:
            logger.debug('Inserting band %s into Bands with id %d', band, band_id)
            cur.execute('insert into Bands ' + 
                        '(band_id,band,band_url,country,genre,status,insert_date) ' + 
                        "values (?,?,?,?,?,?,datetime('now'))",
                        (band_id,band,band_url,country,genre,status))
    
    def insertBasicReviewInfo(self, review_info):
        """
        Inserts basic review info into the Reviews table.
        Also does the following:
            - inserts basic album info
            - inserts basic reviewer info
        """
        year = int(review_info['year'])
        month = int(review_info['month'])
        day = int(review_info['day'])
        hour = int(review_info['hour'])
        minute = int(review_info['minute'])
        modified_date = datetime.datetime(year,month,day,hour,minute,0)
        modified_date_str = modified_date.strftime('%F %T') # should be ISO8601 and match DATETIME('NOW') format
        
        #band = review_info['band']
        band_url = review_info['band_url']
        band_id = get_band_id_from_band_url(band_url)
        if band_id is None:
            logger.warning("Skipping a review, since we can't produce a valid band_id from %s", review_info)
            return
        
        album = review_info['album']
        album_url = review_info['album_url']
        album_id = get_album_id_from_album_url(album_url)
        if album_id is None:
            logger.warning("Skipping a review, since we can't produce a valid album_id from %s", review_info)
            return
        
        review_title = review_info['review_title']
        review_url = review_info['review_url']
        review_percentage = review_info['review_percentage']
        user_id = get_user_id_from_review_url(review_url)
        if user_id is None:
            logger.warning("Skipping a review, since we can't produce a valid user_id from %s", review_info)
            return
        
        user = review_info['reviewer']
        user_url = review_info['reviewer_url']
        
        cur = self.connection.cursor()
        
        self.insertBasicAlbumInfo(band_id, album_id, album, album_url)
        self.insertBasicUserInfo(user_id, user, user_url)
        
        # check if review is already in the DB
        cur.execute('select band_id,album_id,user_id from Reviews where band_id=? and album_id=? and user_id=?',
                    (band_id,album_id,user_id))
        rows = cur.fetchall()
        
        if len(rows) > 1:
            raise RuntimeError("More than one review matches query.  That's a bug.")
        
        elif len(rows) == 1:
            # already exists; don't do anything
            return
            
        else:
            logger.debug('Inserting review for band_id%d, album_id=%d, user_id=%d into Reviews', band_id, album_id, user_id)
            cur.execute('insert into Reviews ' + 
                        '(band_id,album_id,user_id,modified_date,insert_date,' +
                        'review_title,review_url,review_percentage) ' + 
                        "values (:band_id,:album_id,:user_id,:modified_date,datetime('now')," +
                        ':review_title,:review_url,:review_percentage)',
                        {'band_id': band_id,
                         'album_id': album_id,
                         'user_id': user_id,
                         'modified_date': modified_date_str,
                         'review_title': review_title,
                         'review_url': review_url,
                         'review_percentage': review_percentage,
                         })
    
    def insertBasicAlbumInfo(self, band_id, album_id, album, album_url):
        cur = self.connection.cursor()
        
        cur.execute('select album_id from Albums where album_id = ?', (album_id,))
        rows = cur.fetchall()
        
        if len(rows) > 1:
            raise RuntimeError("More than one album_id matches query.  That's a bug.")
        
        elif len(rows) == 1:
            # already exists; don't do anything
            return
        
        else:
            logger.debug('Inserting album %s into Albums with id %d', album, album_id)
            cur.execute('insert into Albums ' + 
                        "(album_id,band_id,album,album_url,insert_date) values (?,?,?,?,datetime('now'))",
                        (album_id,band_id,album,album_url))
    
    def insertBasicUserInfo(self, reviewer_id, reviewer, reviewer_url):
        cur = self.connection.cursor()
        
        cur.execute('select user_id from Users where user_id = ?', (reviewer_id,))
        rows = cur.fetchall()
        
        if len(rows) > 1:
            raise RuntimeError("More than one user matches query.  That's a bug.")
        
        elif len(rows) == 1:
            # already exists; don't do anything
            return
        
        else:
            logger.debug('Inserting user %s into Users', reviewer)
            cur.execute('insert into Users ' + 
                        "(user_id,user,user_url,insert_date) values (?,?,?,datetime('now'))",
                        (reviewer_id,reviewer,reviewer_url))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape metal-archives.com band pages.')
    parser.add_argument('database', type=str,
                        help='Filename of sqlite3 database; must already exist')
    parser.add_argument('band_list', type=str,
                        help='Filename of CSV file produced by BandListScraper')
    parser.add_argument('review_list', type=str,
                        help='Filename of CSV file produced by ReviewListScraper')

    #subparsers?
    parser.add_argument('--logging-level', type=int, default=logging.WARNING,
                        help="Set the logging level")
    
    args = parser.parse_args()
    
    logging.basicConfig(stream=tqdmForLogging, level=args.logging_level)
    
    scraper = InsertBasicInfo(args.database,
                              )
    
    scraper.run(args.band_list, args.review_list)
    