
import datetime, time

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class BaseScraper(object):
    def __init__(self):
        self.base_url = 'https://www.metal-archives.com'
        
        # from their robots.txt
        self.crawl_delay = 3 # seconds
        
        print('Creating Session')
        self.session = requests.Session()
        
        # https://stackoverflow.com/a/35636367
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # metal-archives requires us to have a user agent?
        self.session.headers['user-agent'] = 'bot'
        
        self._last_request_time = None
    
    def sessionGet(self, *args, **kwargs):
        """ Call self.session.get(*args, **kwargs) """
        if self._last_request_time is not None:
            date = datetime.datetime.utcnow()
            sleep_time = self.crawl_delay - (date - self._last_request_time).total_seconds()
            sleep_time = max(0, sleep_time)
            #print('Sleeping for {} seconds'.format(sleep_time))
            time.sleep(sleep_time)
        
        response = self.session.get(*args, **kwargs)
        self._last_request_time = datetime.datetime.utcnow()
        
        return response
    
    def close(self):
        print('Closing Session')
        self.session.close()