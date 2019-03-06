

def get_ID_from_band_URL(band_url):
    return int(band_url.split('/')[-1])

def get_ID_from_album_URL(album_url):
    return int(album_url.split('/')[-1])

def get_ID_from_review_URL(review_url):
    return int(review_url.split('/')[-1])
