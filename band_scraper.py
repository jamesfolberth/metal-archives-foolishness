import argparse, datetime, os, json, csv

import bs4

from baseScraper import BaseScraper
 
class BandScraper(BaseScraper):
    """
    Collects brief band info from https://www.metal-archives.com/browse/letter
    """
    def __init__(self, outfile='', test=False):
        """
        Params:
            outfile - where to put CSV
            test - do a shorter test instead of a full run
        """
        super().__init__()
        
        if not outfile:
            date = datetime.datetime.utcnow()
            date_str = date.strftime('%Y%m%d_%H%M%S')
            outfile = 'metal-archives_bands_' + date_str + '.csv'
        self.outfile = str(outfile)
        print('Will output band data to', self.outfile)
        
        self.test = bool(test)
        if self.test:
            print('Doing a shorter test run instead of a full scrape')
        
        # letters used in the browse tabs: A-Z, NBR, ~
        self.letters = ['NBR', '~']
        self.letters.extend(map(chr, range(ord('A'), ord('Z')+1)))
        
        if self.test:
            self.letters = ['A', 'B']
        
        print('Using letters =', self.letters)
        
        # seems their API requires getting 500 bands at a time 
        self.display_length = 500
        
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
        for letter in self.letters:
            print('Getting stuff for letter =', letter)
            
            # Make the first request
            # That will tell us the total number of entries for this letter
            start = 0
            data = self.makeRequest(letter, start=start)
            
            self.writeBandData(data['aaData'])
           
            total_records = data['iTotalRecords']
            total_records_sum += total_records
            print('There are {} records for letter "{}"'.format(total_records, letter))
            
            n_do = max(0, total_records - self.display_length) // self.display_length + 1
            if self.test:
                n_do = min(2, n_do)
            print('Going to do {} more requests'.format(n_do))
            
            # Now make all the other requests
            for _ in range(n_do):
                start += self.display_length
                data = self.makeRequest(letter, start=start)
            
                self.writeBandData(data['aaData'])
        
        self.close()
        self.closeOutfile()
        
        print('There should be {} rows in {}'.format(total_records_sum+1, self.outfile))
    
    def close(self):
        super().close()
         
    def makeRequest(self, letter, start=0):
        """
        Make a GET request and return the JSON response as a dict
        """
        url = self.base_url + '/browse/ajax-letter/l/' + str(letter) + '/json/1'
        
        if start % self.display_length != 0:
            raise RuntimeError("Bug in the scraper.  In experiments, it appears "
                               "iDisplayStart must be a multiple of {}".format(self.display_length))
        
        payload = {'sEcho': '',
                   'iDisplayStart': start,
                   'iDisplayLength': self.display_length}
        
        print('Making request for letter={} start={}'.format(letter, start))
        response = self.sessionGet(url, params=payload)
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print('Looks like the response is not JSON...')
            raise e
        
        return data
    
    def openOutfile(self):
        self.outfile_handle = open(self.outfile, 'w')
        
        fieldnames = ('band_url', 'band', 'country', 'genre', 'status')
        self.outfile_writer = csv.DictWriter(self.outfile_handle, fieldnames)
        self.outfile_writer.writeheader()
    
    def writeBandData(self, band_data):
        """
        Writes band data to the outfile.
        
        Takes band data of the form
        ["<a href='https://www.metal-archives.com/bands/Abducted/3540381624'>Abducted</a>",
         'Spain',
         'Thrash Metal',
         '<span class="split_up">Split-up</span>']
        
        and cleans it up a bit.  Specifically, this stores the URL (from href), name (from text),
        country, genre, and status (from text).
        
        This isn't the most performant implementation, but that's okay since
        we're gonna be sleeping between requests so we're not blasting MA's
        servers.
        """
        for data_list in band_data:
            soup = bs4.BeautifulSoup(data_list[0], 'html5lib')
            soup2 = bs4.BeautifulSoup(data_list[3], 'html5lib')
            
            name = soup.a.text
            url = soup.a.get('href')
            country = data_list[1]
            genre = data_list[2]
            status = soup2.span.text
            
            self.outfile_writer.writerow({'band': name,
                                          'band_url': url,
                                          'country': country,
                                          'genre': genre,
                                          'status': status})
    
    def closeOutfile(self):
        self.outfile_handle.close()
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape metal-archives.com for all bands.')
    parser.add_argument('--outfile', type=str, default=None,
                        help='filename of output CSV file')
    parser.add_argument('--test', action='store_true',
                        help='Do a shorter test run instead of a full scrape')

    args = parser.parse_args()
    
    scraper = BandScraper(outfile=args.outfile,
                          test=args.test,
                          )
    scraper.run()
    