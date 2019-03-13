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

I guess the thought is that I can get the artist page for all artists (127500 at the time of writing!) and scrape the info.
I think this really should go in a database of some sort.
Then I'll need to have a thing that periodically updates each artist's entry in the DB.

Assuming it takes 3 seconds to get each artist page, it will take 4.5 days to get all these pages.
Dang, that's a long time.
Let's head down that road and see what happens...


### TODO
Can get the band comment via https://www.metal-archives.com/band/read-more/id/126117, where 126117 is the `band_id`

Store similarity scores (from user votes, I think) in Similarities table, where we can lookup based on `band_id`.
This is maybee the preferred approach, at least versus serializing an array of IDs into a string stored as TEXT.
https://stackoverflow.com/a/20139713
https://www.sqlite.org/foreignkeys.html


I think that almost everything in the database can be populated from the band page.
Some of the details in Albums table, the full review text in Reviews, and all of AlbumLineup cannot be populated.
But this should be plenty good enough to get started.



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
Scrape the band page (which requires 
NOTE: this will take many days!
```
python band_page_scraper.py database.db --only-if-not-scraped --skip-full-comment --skip-discography --order-by-reviews
```

But we can still probably do some interesting things with just the data we have at this point.


---

`review_thing.py` is just a one-off experiment
