## Messing around with metal-archives.com data
Let's scrape some data from metal-archives.com and see if we can do something interesting.

I think I'm gonna use the list of all artists as the entrypoint.
```
python band_scraper.py
```

I guess the thought is that I can get the artist page for all artists (127500 at the time of writing!) and scrape the info.
I think this really should go in a database of some sort.
Then I'll need to have a thing that periodically updates each artist's entry in the DB.

Assuming it takes 3 seconds to get each artist page, it will take 4.5 days to get all these pages.
Dang, that's a long time.
Let's head down that road and see what happens...


Create the database with
```
sqlite3 data/band_info.db < band_info.sql
```



---

`review_thing.py` is just a one-off experiment
