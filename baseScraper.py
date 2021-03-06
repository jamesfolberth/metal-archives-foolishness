import datetime, time
import logging
logger = logging.getLogger(__name__)

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class BaseScraper(object):
    def __init__(self):
        self.base_url = 'https://www.metal-archives.com'
        
        # from their robots.txt
        self.crawl_delay = 3 # seconds
        
        logger.debug('Creating requests.Session')
        self.session = requests.Session()
        
        # https://stackoverflow.com/a/35636367
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Really don't need to hear about connections being brought up again after server has closed it
        # https://stackoverflow.com/a/37678627
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
        
        # metal-archives requires us to have a user agent?
        self.session.headers['user-agent'] = 'bot'
        
        self._last_request_time = None
        
    def sessionGet(self, *args, **kwargs):
        """ Call self.session.get(*args, **kwargs) """
        if self._last_request_time is not None:
            date = datetime.datetime.utcnow()
            sleep_time = self.crawl_delay - (date - self._last_request_time).total_seconds()
            sleep_time = max(0, sleep_time)
            #logger.debug('Sleeping for {} seconds'.format(sleep_time))
            time.sleep(sleep_time)
        
        self._last_request_time = datetime.datetime.utcnow()
        response = self.session.get(*args, **kwargs)
        
        return response
    
    def close(self):
        logger.debug('Closing requests.Session')
        self.session.close()