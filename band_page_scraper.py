import argparse, os
import sqlite3 as lite
from pprint import pprint
import logging
logger = logging.getLogger(__name__)

import bs4, tqdm

from baseScraper import BaseScraper
from utils import *

class BandPageScraper(BaseScraper):
    def __init__(self,
                 database_filename,
                 only_if_not_scraped=False,
                 limit=-1,
                 order_by_reviews=False):
        """
        Params:
            database - the sqlit3 database, already populated with basic band info
            only_if_not_scraped - only scrape pages that haven't been previously scraped
            limit - only scrape this many pages, then exit
            order_by_reviews - scrape pages in order of decreasing number of reviews,
                              so that we scrape the more popular bands first.  Default is
                              whatever the optimizer chooses (probably by band_id, but 
                              that's not guaranteed).
            
            TODO
            update - deprecate only_if_not_scraped and instead make default behavior to
                     get pages that haven't been gotten before, and then update pages in order
                     of delta between insert date and last modified date?  Or just insert date?
                     Something.  Maybe make another column in the database?
        """
        super().__init__()
        
        if not os.path.isfile(database_filename):
            raise ValueError("database file {} doesn't exist".format(database_filename))
        self.database_filename = database_filename
        
        self.only_if_not_scraped = bool(only_if_not_scraped)
        self.limit = int(limit)
        self.order_by_reviews = bool(order_by_reviews)
    
    def run(self):
        """
        Call .scrapeBandPage() for each band found in the query
        """
        with lite.connect(self.database_filename) as self.connection:
            # How many do we need to do?
            if self.only_if_not_scraped:
                n_do_query = 'select count(band_id) from Bands where modified_date is null'
            else:
                n_do_query = 'select count(band_id) from Bands'
            cursor = self.connection.cursor()
            n_do = cursor.execute(n_do_query).fetchall()[0][0]
            if self.limit >= 0:
                logger.debug('Invoking limit of %d pages', self.limit)
                n_do = min(n_do, self.limit)
            logger.info('Gonna scrape %d band pages', n_do)
            
            # Okay, now do the stuff
            if self.only_if_not_scraped:
                query = 'select band_id,band_url from Bands where modified_date is null'
            else:
                query = 'select band_id,band_url from Bands'
           
            if self.order_by_reviews:
                query += ' order by (select count(*) from Reviews where Reviews.band_id=Bands.band_id) desc'
 
            if self.limit >= 0:
                query += ' limit {}'.format(self.limit)
            
            logger.debug('query = %s', repr(query))
            for band_id,band_url in tqdm.tqdm(cursor.execute(query), total=n_do):
                nrev_cursor = self.connection.cursor()
                num_reviews = nrev_cursor.execute('select count(*) from Reviews where band_id=?', (band_id,)).fetchall()[0][0]
                logger.debug('num_reviews = %d', num_reviews)
                
                self.scrapeBandPage(band_id, band_url)
        
        self.close()
        
    def scrapeBandPage(self, band_id, band_url):
        """
        GET the band page from metal-archives and parse it using bs4.
        This will populate the Bands table with info, but also certain basic info
        in the Albums, Artists, Labels, BandLabel, Similarities, and BandLineup tables.
        
        The the following require a separate request:
         - getting the full band comment
         - getting the (full) album list (aka discography)
         - getting similar bands/recommendations
        """
        # get the band page
        response = self.sessionGet(band_url)
        logger.debug('response status_code=%d', response.status_code)
        if response.status_code != 200:
            raise RuntimeError('Response status is not 200, bailing')
        
        soup = bs4.BeautifulSoup(response.text, 'html5lib')
    
    def scrapeWhatsOnBandPage(self, band_id, band_url, soup):
        """
        Scrape what's available on the band page without making any more requests
        These things are
         - the lyrical themes
         - the added date
         - the modified date
        
        The full comment will require a request
        """
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ScrapeTokenize the genre text for each '
                                     'band in the database.  This updates the '
                                     '`genre_tokens` column.')
    parser.add_argument('database', type=str,
                        help='Filename of sqlite3 database; must already exist '
                        'and have basic band info')
    
    parser.add_argument('--only-if-not-scraped', action='store_true',
                        help="Only scrape pages that haven't previously been scraped "
                        "(as witnessed by `modified_date` being NULL)")
    parser.add_argument('--limit', type=int, default=-1,
                        help='After scraping --limit pages, exit; useful for dev/test')
    parser.add_argument('--order-by-reviews', action='store_true',
                        help='Scrape pages in order of decreasing number of reviews '
                        '(more popular bands first)')
    
    #subparsers?
    parser.add_argument('--logging-level', type=int, default=logging.WARNING,
                        help="Set the logging level")
    
    args = parser.parse_args()
    
    logging.basicConfig(stream=tqdmForLogging, level=args.logging_level)
    
    scraper = BandPageScraper(args.database,
                              only_if_not_scraped=args.only_if_not_scraped,
                              limit=args.limit,
                              order_by_reviews=args.order_by_reviews)
    scraper.run()