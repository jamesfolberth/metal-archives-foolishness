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



---

`review_thing.py` is just a one-off experiment
