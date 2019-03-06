
import re, logging

import bs4
import numpy as np
import matplotlib.pyplot as plt

def get_soup(fn):
    with open(fn, 'r') as f:
        doc = f.read()
    
    soup = bs4.BeautifulSoup(doc, 'html.parser')
    return soup

def main():
    # This album seems quite controversial...
    fn = 'deafheaven_sunbather_reviews.html'
    
    soup = get_soup(fn)
    
    review_scores = []
    percentage_regex = re.compile(r'\d+%')
    for title in soup.find_all('h3', 'reviewTitle'):
        matches = re.findall(percentage_regex, title.text)
        
        if len(matches) != 1:
            logging.warning('Found matches = %s, which is not handled', repr(matches))
            continue

        percent_str = matches[0]
        if percent_str[-1] != '%':
            logging.warning('Match does not end with percentage')
            continue

        review_scores.append(int(percent_str[0:-1]))
    
    plt.figure()
    bins = list(range(0, 101, 10))
    plt.hist(review_scores, bins=bins)
    plt.xticks(bins)
    
    plt.figure()
    plt.plot(review_scores, 0.01*np.random.rand(len(review_scores)), 'kx')
    plt.xticks(bins)
    plt.ylim(-0.1, 0.1)

    plt.show()
    
if __name__ == '__main__':
    main()
