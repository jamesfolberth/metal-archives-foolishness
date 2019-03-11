import argparse, os, re, collections
import sqlite3 as lite
from pprint import pprint
import logging
logger = logging.getLogger(__name__)

import bs4, tqdm

from baseScraper import BaseScraper
from utils import *


MemberStatus = collections.namedtuple('MemberStatus',
                                      ('current',
                                       'current_live',
                                       'past',
                                       'past_live',
                                       'last_known',
                                       'last_known_live',
                                       ))

class BandPageScraper(BaseScraper):
    def __init__(self,
                 database_filename,
                 only_if_not_scraped=False,
                 offset=0,
                 limit=-1,
                 order_by_reviews=False,
                 skip_band_page=False,
                 skip_full_comment=False,
                 skip_recommendations=False,
                 skip_discography=False,
                 no_store=False):
        """
        Params:
            database - the sqlit3 database, already populated with basic band info
            only_if_not_scraped - only scrape pages that haven't been previously scraped
            limit - only scrape this many pages, then exit
            offset - start `offset` rows into the band query
            order_by_reviews - scrape pages in order of decreasing number of reviews,
                              so that we scrape the more popular bands first.  Default is
                              whatever the optimizer chooses (probably by band_id, but 
                              that's not guaranteed).
            skip_band_page - skip requesting the band's page; also enables skip_full_comment
            skip_full_comment - skip requesting the band's full comment/read more text
            skip_recommendations - skip requesting the band's recommended/similar bands
            skip_discography - skip requesting the band's discography
            no_store - don't actually store anything in the database, but still do all the
                       requests and parsing
            
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
        self.offset = int(offset)
        self.order_by_reviews = bool(order_by_reviews)
        self.skip_band_page = bool(skip_band_page)
        self.skip_full_comment = bool(skip_full_comment) or self.skip_band_page
        self.skip_recommendations = bool(skip_recommendations)
        self.skip_discography = bool(skip_discography)
        self.no_store = bool(no_store)
        
        self.soup_features = 'html5lib'
        
        self.date_re = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
        self.added_on_re = re.compile(r'Added on: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
        self.modified_on_re = re.compile(r'Last modified on: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
    
    def run(self):
        """
        Call .getBandPage() for each band found in the query
        """
        with lite.connect(self.database_filename) as self.connection:
            # How many do we need to do?
            if self.only_if_not_scraped:
                n_do_query = 'select count(band_id) from Bands where modified_date is null'
            else:
                n_do_query = 'select count(band_id) from Bands'
            cursor = self.connection.cursor()
            n_queried = cursor.execute(n_do_query).fetchall()[0][0]
            
            if self.limit >= 0:
                logger.debug('Invoking limit of %d pages', self.limit)
                n_do = min(n_queried, self.limit)
            else:
                n_do = n_queried
                
            if self.offset > 0:
                logger.debug('Invoking offset of %d pages', self.offset)
                if self.offset + n_do > n_queried:
                    n_do = max(0, n_queried - self.offset)
            
            logger.info('Gonna scrape %d band pages', n_do)
            
            # Okay, now do the stuff
            if self.only_if_not_scraped:
                query = 'select band_id,band_url from Bands where modified_date is null'
            else:
                query = 'select band_id,band_url from Bands'
           
            if self.order_by_reviews:
                query += ' order by (select count(*) from Reviews where Reviews.band_id=Bands.band_id) desc'
            
            #TODO JMF 10 Mar 2019: this should use lite's parameter substitution
            if self.limit >= 0:
                query += ' limit {}'.format(self.limit)
            
            if self.offset >= 0:
                if self.limit < 0:
                    query += ' limit {}'.format(n_queried)
                query += ' offset {}'.format(self.offset)
            
            logger.debug('query = %s', repr(query))
            for band_id,band_url in tqdm.tqdm(cursor.execute(query), total=n_do):
                if self.order_by_reviews:
                    nrev_cursor = self.connection.cursor()
                    num_reviews = nrev_cursor.execute('select count(*) from Reviews where band_id=?', (band_id,)).fetchall()[0][0]
                    logger.debug('num_reviews = %d', num_reviews)
                
                # Request and scrape the band's page
                if not self.skip_band_page:
                    band_dict, artist_dict_list, band_label_dict_list, label_dict =\
                        self.getBandPage(band_id, band_url)
                else:
                    band_dict = {}
                    artist_dict_list = []
                    band_label_dict_list = []
                    label_dict = {}
                    
                # Request the full band comment/read more text
                if not self.skip_full_comment:
                    comment_body = self.getBandsFullComment(band_id)
                    if not band_dict: # if we didn't get the band page
                        band_dict['band_id'] = band_id
                    band_dict['comment'] = comment_body
                
                # Get similar bands
                if not self.skip_recommendations:
                    similar_band_dict_list = self.getSimilarBands(band_id)
                else:
                    similar_band_dict_list = []
                
                # Get discography
                if not self.skip_discography:
                    album_dict_list = self.getBandsDiscography(band_id)
                else:
                    album_dict_list = []
                
                # Store in database
                if not self.no_store:
                    self.storeInDatabase(band_id,
                                    band_dict=band_dict,
                                    artist_dicts=artist_dict_list,
                                    bandlabel_dicts=band_label_dict_list,
                                    label_dict=label_dict,
                                    similarity_dicts=similar_band_dict_list,
                                    album_dicts=album_dict_list)
        
        self.close()
        
    def getBandPage(self, band_id, band_url):
        """
        GET the band page from metal-archives and parse it using bs4.
        This returns dicts and lists of dicts suitable for inserting into
        the Bands, Artists, BandLineup, and Labels tables of the database.
        
        Though they appear on the band's page, the following each require a
        separate request:
         - getting the full band comment
         - getting the (full) album list (aka discography)
         - getting similar bands/recommendations
        """
        # dict mapping table name to a dict (or list of dicts) of column: data.
        # We'll populate this dict first, and then store all the data at once,
        # storing the modified_date last, since that is the sentinel for a fully
        # scraped band page.  Since we're gonna be pausing between requests, speed
        # isn't a concern so we'll just store one band scrape at a time.
        #store_in_db = {}
        
        # get the band page
        logger.debug('GET band page for band_id=%d', band_id)
        response = self.sessionGet(band_url)
        if response.status_code != 200:
            raise RuntimeError('Got response status {}, bailing.'.format(response.status_code))
        
        band_soup = bs4.BeautifulSoup(response.text, self.soup_features)
        added_on, modified_on, lyrical_themes, label_dict = self.scrapeWhatsOnBandPage(band_id, band_soup)
        
        band_dict = {'band_id': band_id,
                     'added_date': added_on,
                     'modified_date': modified_on,
                     'themes': lyrical_themes,
                     }
        
        # get the lineup from the band page
        artists, band_lineup_entries = self.getBandsLineup(band_id, band_soup)
        
        return band_dict, artists, band_lineup_entries, label_dict
    
    def scrapeWhatsOnBandPage(self, band_id, soup):
        """
        Scrape what's available on the band page without making any more requests
        These things are
         - the lyrical themes
         - the added date
         - the modified date
         - the band's label (returned as a dict of label_id, label, label_url)
        
        Getting the full comment will require a request
        """
        # get the band name; check that ID in url matches band_id
        band_name_list = soup.find_all('h1', 'band_name')
        if len(band_name_list) != 1:
            raise RuntimeError('Got bad band_name_list = {} for band_id={}'.format(band_name_list, band_id))
        band_name_tag = band_name_list[0]
        band_id_check = get_band_id_from_band_url(band_name_tag.a.get('href'))
        if band_id != band_id_check:
            raise RuntimeError('Got incorrect band_id={} from band name href (band_id={} in db)'.format(
                band_id_check, band_id))
        
        # Get the lyrical themes
        stats_div = soup.find('div', {'id': 'band_stats'})
        right_stuff = stats_div.find('dl', 'float_right')
        dd_list = right_stuff.find_all('dd')
        lyrical_themes = dd_list[1].text
        
        # Get the current label
        label_tag = dd_list[2].a
        label = label_tag.text
        label_url = label_tag.get('href')
        label_id = get_label_id_from_label_url(label_url)
        label_dict = {'label_id': label_id,
                      'label': label,
                      'label_url': label_url}
        
        # Get the added/modified dates
        audit_div = soup.find('div', {'id': 'auditTrail'})
        td_list = audit_div.find_all('td')
        added_on_td = td_list[2]
        added_on_match = re.match(self.added_on_re, added_on_td.text)
        if not added_on_match:
            raise RuntimeError("Didn't find added on date for band_id={}".format(band_id))
        added_on = added_on_match.group(1)
        
        modified_on_td = td_list[3]
        modified_on_match = re.match(self.modified_on_re, modified_on_td.text)
        if not modified_on_match:
            raise RuntimeError("Didn't find modified on date for band_id={}".format(band_id))
        modified_on = modified_on_match.group(1)
        
        return added_on, modified_on, lyrical_themes, label_dict
    
    def getBandsFullComment(self, band_id):
        """
        GET the band's "read-more"/full comment.
        Return the <body> (with <body> tags removed).
        """
        logger.debug('GET band read-more page for band_id=%d', band_id)
        read_more_url = 'https://www.metal-archives.com/band/read-more/id/' + str(band_id)
        response = self.sessionGet(read_more_url)
        if response.status_code != 200:
            raise RuntimeError('Got response status {}, bailing.'.format(response.status_code))
        
        soup = bs4.BeautifulSoup(response.text, self.soup_features)
        return ''.join(map(str, soup.body.children))
    
    def getBandsLineup(self, band_id, soup):
        """
        Parse the band's complete members table to get basic info about
        artists and create dicts with info for storing into the Artists and BandLineup
        tables.
           
        Split-up and name-changed bands don't have a complete lineup, but instead show
        the current lineup under the title of "Last Known Lineup".  In these cases, we'll
        use the current lineup.
        """
        logger.debug('Scraping band page for members')
        
        # figure out which tabs we have
        band_members_tag = soup.find('div', {'id': 'band_members'})
        tab_links = band_members_tag.ul.find_all('li')
        
        have_complete = False
        have_current = False
        current_tab_name = ''
        for link in tab_links:
            href = link.a.get('href')
            if href == '#band_tab_members_all':
                have_complete = True
            elif href == '#band_tab_members_current':
                have_current = True
                current_tab_name = link.a.text
        
        if have_complete:
            logger.debug('Got complete members table')
            complete_members_tag = band_members_tag.find('div', {'id': 'band_tab_members_all'})
            return self.parseMembersTable(band_id, complete_members_tag.table)
        
        logger.debug('No complete members table (e.g. if band has no past/live members, '
                     'is split-up, on-hold, or changed name')
        
        if have_current:
            logger.debug('Got a current members table...')
            current_members_tag = band_members_tag.find('div', {'id': 'band_tab_members_current'})
            
            if current_tab_name == 'Current lineup':
                logger.debug("it's the band's current lineup")
                member_status = MemberStatus(True,False,False,False,False,False)
            elif current_tab_name == 'Last known lineup':
                logger.debug("it's the band's last known lineup (split-up, on-hold, or changed name)")
                member_status = MemberStatus(False,False,False,False,True,False)
            else:
                raise NotImplementedError(f"Didn't handle current_tab_name={current_tab_name}")
                
            return self.parseMembersTable(band_id, current_members_tag.table, member_status)
        
        raise NotImplementedError('No complete or current members table...')
    
    def parseMembersTable(self, band_id, table, member_status=None):
        """
        Parse a band's member table, which could be the complete lineup or current/last known lineup.
        """
        def get_class(row):
            classes = row.get('class')
            if not classes:
                raise RuntimeError('Band member row without a class: row={}'.format(row))
            
            if len(classes) != 1:
                raise RuntimeError('Band member row with zero or 2+ classes: row={}'.format(row))
            
            return str(classes[0])
        
        members = []
        rows = table.tbody.find_all('tr')
        i = 0
        while i < len(rows):
            row = rows[i]
            c = get_class(row)
            
            if c == 'lineupHeaders':
                text = str(row.td.text).strip().rstrip()
                text = re.sub(r'\s+', ' ', text)
                
                if text == 'Current':
                    member_status = MemberStatus(True,False,False,False,False,False)
                elif text == 'Current (Live)':
                    member_status = MemberStatus(False,True,False,False,False,False)
                elif text == 'Past':
                    member_status = MemberStatus(False,False,True,False,False,False)
                elif text == 'Past (Live)':
                    member_status = MemberStatus(False,False,False,True,False,False)
                elif text == 'Last known':
                    member_status = MemberStatus(False,False,False,False,True,False)
                elif text == 'Last known (Live)':
                    member_status = MemberStatus(False,False,False,False,False,True)
                else:
                    raise NotImplementedError('Unhandled lineupHeaders text={}'.format(text))
                
                i += 1
                continue
            
            elif c == 'lineupRow':
                if member_status is None:
                    raise NotImplementedError("Didn't properly handle getting member status "
                                              "from member tab name")
                
                artist_tag = row.td
                a_tags = artist_tag.find_all('a')
                
                if len(a_tags) == 0: # no artist page for this memer
                    i += 1
                    if i < len(rows):
                        if get_class(rows[i]) == 'lineupBandsRow': # skip the see also if it exists
                            i += 1
                    continue
                
                elif len(a_tags) > 1:
                    raise NotImplementedError("Unhandled case... multiple artists pages?")
                
                a_tag = a_tags[0]
                artist = a_tag.text
                artist_url = a_tag.get('href')
                artist_id = get_artist_id_from_artist_url(artist_url)
                
                member = {'artist_id': artist_id,
                          'artist': artist,
                          'artist_url': artist_url,
                          'status': member_status,
                          }
                
                i += 1
                if i < len(rows):
                    if get_class(rows[i]) == 'lineupBandsRow':
                        # this member has a see also row
                        # We likely don't need to do anything with this though,
                        # since the BandLineup table will show these connections
                        # once the table is built up.
                        i += 1
                
                members.append(member)
                continue
                
            elif c == 'lineupBandsRow':
                raise RuntimeError('Bug in implementation of member list iteration')
                
            else:
                raise NotImplementedError("Didn't code up handling for band member row class={}".format(c))
        
            raise RuntimeError('Bug in implementation of member list iteration')
        
        # Check if we have the same artist twice in the members list
        members_dict = {}
        for i, member in enumerate(members):
            artist_id = member['artist_id']
            if artist_id in members_dict:
                member0 = members_dict[artist_id]
                status0 = member0['status']
                status1 = member['status']
                
                status = MemberStatus(current=status0.current or status1.current,
                                      current_live=status0.current_live or status1.current_live,
                                      past=status0.past or status1.past,
                                      past_live=status0.past_live or status1.past_live,
                                      last_known=status0.last_known or status1.last_known,
                                      last_known_live=status0.last_known_live or status1.last_known_live,
                                      )
                member0['status'] = status
                
            else:
                members_dict[artist_id] = member
                
        # Now build a list of artists and band-lineup suitable for entry into the db
        artists = []
        band_lineup_entries = []
        for member in members_dict.values():
            artists.append({'artist_id': member['artist_id'],
                            'artist': member['artist'],
                            'artist_url': member['artist_url']})
            
            status = member['status']
            band_lineup_entries.append({'band_id': band_id,
                                        'artist_id': member['artist_id'],
                                        'current_member': status.current,
                                        'current_live_member': status.current_live,
                                        'past_member': status.past,
                                        'past_live_member': status.past_live,
                                        'last_known_member': status.last_known,})
        
        return artists, band_lineup_entries
    
    def getSimilarBands(self, band_id):
        """
        GET similar bands via /band/ajax-recommendations/id/ and parse the table into
        a list of dicts suitable for storage into Similarities table.
        """
        logger.debug('GET band recommendations for band_id=%d', band_id)
        similar_bands_url = 'https://www.metal-archives.com/band/ajax-recommendations/id/' + str(band_id)
        params = {'showMoreSimilar': 1}
        response = self.sessionGet(similar_bands_url, params=params)
        if response.status_code != 200:
            raise RuntimeError('Got response status {}, bailing.'.format(response.status_code))
        
        soup = bs4.BeautifulSoup(response.text, self.soup_features)
        table = soup.find('table', {'id': 'artist_list'})
        
        recommendations = []
        for row in table.tbody.find_all('tr'):
            cells = row.find_all('td')
            
            if len(cells) < 4:
                # end of table, verify, then break
                tag = cells[0]
                if tag.get('id') == 'show_more':
                    break
            
            artist_tag = cells[0]
            similar_to_id = get_band_id_from_band_url(artist_tag.a.get('href'))
            score = int(cells[3].text)
            
            recommendations.append({'band_id': band_id,
                                    'similar_to_id': similar_to_id,
                                    'score': score})
        
        return recommendations
    
    def getBandsDiscography(self, band_id):
        """
        GET a band's discography via /band/discography/id/{band_id}/tab/all and parse the table into
        a list of dicts suitable for storage into Albums table.
        """
        logger.debug('GET band discography for band_id=%d', band_id)
        discog_url = f'https://www.metal-archives.com/band/discography/id/{band_id}/tab/all'
        response = self.sessionGet(discog_url)
        if response.status_code != 200:
            raise RuntimeError('Got response status {}, bailing.'.format(response.status_code))
        
        soup = bs4.BeautifulSoup(response.text, self.soup_features)
        table = soup.find('table', {'class': 'display discog'})
        
        if not table:
            raise RuntimeError("Didn't get the discography table")
        
        albums = []
        for row in table.tbody.find_all('tr'):
            cells = row.find_all('td')
            album_tag = cells[0].a
            album = album_tag.text
            album_url = album_tag.get('href')
            album_id = get_album_id_from_album_url(album_url)
    
            type_tag = cells[1]
            type_str = type_tag.text
    
            year_tag = cells[2]
            year = int(year_tag.text)
            
            albums.append({'band_id': band_id,
                           'album_id': album_id,
                           'album': album,
                           'album_url': album_url,
                           'type': type_str,
                           'release_date': year,
                           })
        
        return albums
    
    def storeInDatabase(self,
                        band_id,
                        band_dict=None,
                        artist_dicts=[],
                        bandlabel_dicts=[],
                        label_dict=None,
                        similarity_dicts=[],
                        album_dicts=[],
                        ):
        """
        Store things in the database.
        """
        cursor = self.connection.cursor()
        
        logger.warning("storing in db not implemented")
        raise NotImplementedError()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape the band page for each band in the db,'
                                     ' also making a few other GET requests and scrapes.')
    parser.add_argument('database', type=str,
                        help='Filename of sqlite3 database; must already exist '
                        'and have basic band info')
    
    parser.add_argument('--only-if-not-scraped', action='store_true',
                        help="Only scrape pages that haven't previously been scraped "
                        "(as witnessed by `modified_date` being NULL)")
    parser.add_argument('--limit', type=int, default=-1,
                        help='After scraping --limit pages, exit; useful for dev/test')
    parser.add_argument('--offset', type=int, default=0,
                        help='Start --offset rows into the band query; useful for dev/test')
    parser.add_argument('--order-by-reviews', action='store_true',
                        help='Scrape pages in order of decreasing number of reviews '
                        '(more popular bands first)')
    
    parser.add_argument('--skip-band-page', action='store_true',
                        help="Skip requesting the band's page; also enables --skip-full-comment")
    parser.add_argument('--skip-full-comment', action='store_true',
                        help="Skip requesting the band's full comment/read more")
    parser.add_argument('--skip-recommendations', action='store_true',
                        help="Skip requesting the band's recommended/similar bands")
    parser.add_argument('--skip-discography', action='store_true',
                        help="Skip requesting the band's discography")
    
    parser.add_argument('--no-store', action='store_true',
                        help="Don't actually store anything in the database")
    
    #subparsers?
    parser.add_argument('--logging-level', type=int, default=logging.WARNING,
                        help="Set the logging level")
    
    args = parser.parse_args()
    
    logging.basicConfig(stream=tqdmForLogging, level=args.logging_level)
    
    scraper = BandPageScraper(args.database,
                              only_if_not_scraped=args.only_if_not_scraped,
                              limit=args.limit,
                              offset=args.offset,
                              order_by_reviews=args.order_by_reviews,
                              skip_band_page=args.skip_band_page,
                              skip_full_comment=args.skip_full_comment,
                              skip_recommendations=args.skip_recommendations,
                              skip_discography=args.skip_discography,
                              no_store=args.no_store,
                              )
    scraper.run()