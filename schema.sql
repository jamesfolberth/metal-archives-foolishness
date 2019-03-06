drop table if exists Bands;
create table Bands (
    band_id integer primary key not null,

    added_date text, /* date added to MA */
    modified_date text, /* date modified on MA */
    insert_date text, /* date entry in DB inserted/updated */

    band text not null,
    band_url text not null,
    country text,
    status text,
    genre text,
    themes text,
    comment text
);

drop table if exists Albums;
create table Albums (
    album_id integer primary key not null,
    band_id integer not null, /* id into Bands table */

    added_date text, /* date added to MA */
    modified_date text, /* date modified on MA */
    insert_date text, /* date entry in DB inserted/updated */

    album text not null,
    album_url text not null,
    type text,
    release_date text,
    foreign key(band_id) references Bands(band_id)
);

drop table if exists Artists;
create table Artists (
    artist_id integer primary key not null,

    added_date text, /* date added to MA */
    modified_date text, /* date modified on MA */
    insert_date text, /* date entry in DB inserted/updated */

    artist text not null,
    artist_url text not null,
    origin text,
    comment text
);

drop table if exists Reviews;
create table Reviews (
    review_id integer primary key not null,
    band_id integer not null, /* id into Bands table */
    album_id integer not null, /* id into Albums table */
    user_id integer not null, /* id into Users table */
    
    modified_date text, /* date modified on MA */
    insert_date text, /* date entry in DB inserted/updated */
    
    review text, /* the full review text */
    review_url text,
    review_percentage integer,
    
    foreign key(band_id) references Bands(band_id),
    foreign key(album_id) references Albums(album_id),
    foreign key(user_id) references Users(user_id)
);

drop table if exists Users;
create table Users (
    user_id integer primary key autoincrement, /* MA doesn't appear to have an ID for users */

    insert_date text, /* date entry in DB inserted/updated */

    user text, /* MA username; expected to be unique */
    user_url text
);

drop table if exists Similarities;
create table Similarities (
    id integer primary key autoincrement, /* don't really care about this id */

    insert_date text, /* date entry in DB inserted/updated */

    band_id integer not null, /* id into Bands table */
    similar_to_id integer not null, /* id into Bands table */
    score integer not null, /* similarity score = users' votes */

    foreign key(band_id) references Bands(band_id),
    foreign key(similar_to_id) references Bands(band_id)
);

drop table if exists BandLineup;
create table BandLineup (
    id integer primary key autoincrement,
    band_id integer not null, /* id into Bands table */
    artist_id integer not null, /* id into Artists table */
 
    insert_date text, /* date entry in DB inserted/updated */
    
    current_member integer,
    current_live_member integer,
    past_member integer,
    past_live_member integer,
    
    foreign key(band_id) references Bands(band_id),
    foreign key(artist_id) references Artists(artist_id)
);

drop table if exists AlbumLineup;
create table AlbumLineup (
    id integer primary key autoincrement,
    band_id integer not null, /* id into Bands table */
    artist_id integer not null, /* id into Artists table */
    
    insert_date text, /* date entry in DB inserted/updated */
    
    band_member integer,
    guest_session integer,
    misc_staff integer,

    foreign key(band_id) references Bands(band_id),
    foreign key(artist_id) references Artists(artist_id)
);

