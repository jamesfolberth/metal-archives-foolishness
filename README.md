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



Create the database with
```
sqlite3 data/database.db < schema.sql
```



---

`review_thing.py` is just a one-off experiment
