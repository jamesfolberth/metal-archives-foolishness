import argparse, datetime, os, json, csv
import logging
logger = logging.getLogger(__name__)

import bs4

from baseScraper import BaseScraper
 
class ReviewListScraper(BaseScraper):
    """
    Collects brief review info from https://www.metal-archives.com/review/browse
    """
    def __init__(self, outfile='', start='200207', stop=''):
        """
        Params:
            outfile - where to put CSV
            test - do a shorter test instead of a full run
        """
        super().__init__()
        
        if not outfile:
            date = datetime.datetime.utcnow()
            date_str = date.strftime('%Y%m%d_%H%M%S')
            outfile = 'metal-archives_review_list_' + date_str + '.csv'
        self.outfile = str(outfile)
        print('Will output band data to', self.outfile)
        
        self.start = datetime.date(year=int(start[0:4]), month=int(start[4:6]), day=1)
        
        if not stop:
            self.stop = datetime.date.today()
        else:
            self.stop = datetime.date(year=int(stop[0:4]), month=int(stop[4:6]), day=1)
        
        # seems their API requires getting 200 reviews at a time 
        self.display_length = 200
        
    def run(self):
        """
        Do the stuff.  Will close things at the end of .run()
        """
        # check if the output file already exists and ask the user if they wish to overwrite
        if os.path.isfile(self.outfile):
            print('The outfile "{}" already exists.'.format(self.outfile))
            response = input('Overwrite (y/n): ').lower()
            if response != 'y':
                print('Okay, bailing')
                return
            else:
                print('Okay, will overwrite')
        
        self.openOutfile()
        
        total_records_sum = 0
        
        start_year = self.start.year
        start_month = self.start.month
        
        stop_year = self.stop.year
        stop_month = self.stop.month
        
        for year in range(start_year, stop_year+1):
            for month in range(start_month if year == start_year else 1,
                               stop_month+1 if year == stop_year else 12+1):
            
                date_str = '{:04d}-{:02d}'.format(year, month)
                print('Getting stuff for ', date_str)
                
                # Make the first request
                # That will tell us the total number of entries for this month
                start = 0
                data = self.makeRequest(date_str, start=start)
            
                self.writeReviewData(data['aaData'], year, month)
           
                total_records = data['iTotalRecords']
                total_records_sum += total_records
                print('There are {} records for {}'.format(total_records, date_str))
            
                n_do = max(0, total_records - self.display_length) // self.display_length + 1
                print('Going to do {} more requests'.format(n_do))
            
                # Now make all the other requests
                for _ in range(n_do):
                    start += self.display_length
                    data = self.makeRequest(date_str, start=start)
           
                    self.writeReviewData(data['aaData'], year, month)
        
        self.close()
        self.closeOutfile()
        
        print('There should be {} rows in {}'.format(total_records_sum+1, self.outfile))
    
    def close(self):
        super().close()
         
    def makeRequest(self, date_str, start=0):
        """
        Make a GET request and return the JSON response as a dict
        """
        url = self.base_url + '/review/ajax-list-browse/by/date/selection/' + str(date_str) + '/json/1'
        
        if start % self.display_length != 0:
            raise RuntimeError("Bug in the scraper.  In experiments, it appears "
                               "iDisplayStart must be a multiple of {}".format(self.display_length))
        
        payload = {'sEcho': '',
                   'iDisplayStart': start,
                   'iDisplayLength': self.display_length}
        
        print('Making request for date_str={} start={}'.format(date_str, start))
        response = self.sessionGet(url, params=payload)
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print('Looks like the response is not JSON...')
            raise e
        
        return data
    
    def openOutfile(self):
        self.outfile_handle = open(self.outfile, 'w')
        
        fieldnames = ('year', 'month', 'day', 'hour', 'minute',
                      'band', 'band_url', 'album', 'album_url',
                      'review_title', 'review_url', 'review_percentage',
                      'reviewer', 'reviewer_url')
        self.outfile_writer = csv.DictWriter(self.outfile_handle, fieldnames)
        self.outfile_writer.writeheader()
    
    def writeReviewData(self, review_data, year, month):
        """
        Writes review data to the outfile.
        
        Takes review data of the form
            ['January 31',
             '<a href="https://www.metal-archives.com/reviews/Toxik_Attack/Assassinos_em_S%C3%A9rie/746017/Cosmic_Mystery/407515" title="ole skool thrash metal!" class="iconContainer ui-state-default ui-corner-all"><span class="ui-icon ui-icon-search">Read</span></a>',
             '<a href="https://www.metal-archives.com/bands/Toxik_Attack/3540389184">Toxik Attack</a>',
             '<a href="https://www.metal-archives.com/albums/Toxik_Attack/Assassinos_em_S%C3%A9rie/746017">Assassinos em Série</a>',
             '67%',
             '<a href="https://www.metal-archives.com/users/Cosmic%20Mystery" class="profileMenu">Cosmic Mystery</a>',
             '23:18']
        
        and cleans it up a bit.
        """
        for review in review_data:
            day = int(review[0].split()[1])
            hour, minute = map(int, review[6].split(':'))
            
            review_percentage = int(review[4][:-1])
            
            review_soup = bs4.BeautifulSoup(review[1], 'html5lib')
            band_soup = bs4.BeautifulSoup(review[2], 'html5lib')
            album_soup = bs4.BeautifulSoup(review[3], 'html5lib')
            reviewer_soup = bs4.BeautifulSoup(review[5], 'html5lib')
            
            review_url = review_soup.a.get('href')
            review_title = review_soup.a.get('title')
            
            band_url = band_soup.a.get('href')
            band = band_soup.a.text
            
            album_url = album_soup.a.get('href')
            album = album_soup.a.text
            
            reviewer_url = reviewer_soup.a.get('href')
            reviewer = reviewer_soup.a.text

            self.outfile_writer.writerow({'year': year,
                                          'month': month,
                                          'day': day,
                                          'hour': hour,
                                          'minute': minute,
                                          'band': band,
                                          'band_url': band_url,
                                          'album': album,
                                          'album_url': album_url,
                                          'review_title': review_title,
                                          'review_url': review_url,
                                          'review_percentage': review_percentage,
                                          'reviewer': reviewer,
                                          'reviewer_url': reviewer_url})

    def closeOutfile(self):
        self.outfile_handle.close()
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape metal-archives.com for all reviews.')
    parser.add_argument('--outfile', type=str, default=None,
                        help='filename of output CSV file')
    parser.add_argument('--start', type=str, default='200207',
                        help='Start date in YYYYMM form.  Earliest is 200207.')
    parser.add_argument('--stop', type=str, default='',
                        help='Stop date in YYYYMM form.  Defaults to now')


    args = parser.parse_args()
    
    scraper = ReviewListScraper(outfile=args.outfile,
                                start=args.start,
                                stop=args.stop,
                                )
    scraper.run()
    