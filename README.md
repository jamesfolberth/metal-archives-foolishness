## Messing around with metal-archives.com data
Let's scrape some data from metal-archives.com and see if we can do something interesting.

I think I'm gonna use the list of all artists as the entrypoint.
```
python band_scraper.py
```

It was easy to also make a review scraper:
```
python review_scraper.py
```


## Expected usage
Scrape band and reviews lists.
```
python band_list_scraper.py
python review_list_scraper.py
```
Now we should have two files: `metal-archives_band_list_YYYYMMDD_HHMMSS.csv` and `metal-archives_review_list_YYYYMMDD_HHMMSS.csv`.

We can collect basic info from these CSVs and put it in the database.
```
sqlite3 database.db < schema.sql # create the db if it doesn't already exist
python insert_basic_info.py database.db metal-archives_band_list_YYYYMMDD_HHMMSS.csv metal-archives_review_list_YYYYMMDD_HHMMSS.csv
```

We can go ahead and tokenize the genre texts, which are conveniently included in the band list.
```
python genre_tokenizer.py database.db
```

Now the database exists, but it only has some of the info we might want.
For example, we only have albums that have been reviewed, we only have users
that have submitted reviews, we don't have extra info from scraping the band page, etc.
It will take scraping each bands page to get more complete info.
In particular, the similarity score (users' votes) seems interesting.
Scrape the band pages (which will take a while!):
```
python band_page_scraper.py database.db --only-if-not-scraped --skip-full-comment --skip-discography --order-by-reviews --reviews-gt 0
```

## Graph/Visualization ideas?
https://github.com/d3/d3/wiki/Gallery

http://www.findtheconversation.com/concept-map/
http://www.redotheweb.com/CodeFlower/

Adjust the graph based on similarity level, which is pretty neat
http://www.cotrino.com/2012/11/language-network/

http://emptypipes.org/2015/02/15/selectable-force-directed-graph/
http://emptypipes.org/2017/04/29/d3v4-selectable-zoomable-force-directed-graph/

http://bl.ocks.org/paulovn/9686202

http://sigmajs.org/

Looks like the python offerings are networkx, igraph, graphtool, and graphviz (pydot)
https://ipython-books.github.io/64-visualizing-a-networkx-graph-in-the-notebook-with-d3js/

I tried just throwing the whole review graph with outdegree > 1.  lol, it was dog slow.
So gotta do something smarter, I guess.
Maybe like pick a band and then show all connections <= k hops away.  This is maybe called the ego subgraph.
https://bl.ocks.org/heybignick/3faf257bbbbc7743bb72310d03b86ee8

---

`review_thing.py` is just a one-off experiment
