drop table if exists tracks;
create table tracks (
    id integer primary key autoincrement,
    user_id string not null,
    timestamp integer not null,
    referrer string,
    destination string not null
);
