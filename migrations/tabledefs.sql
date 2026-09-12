-- 1 up
create table episodes (id text,feed text, title text, description text, published_epoch integer, url text, handeled_epoch integer, is_downloaded integer, is_rejected integer, priority integer, PRIMARY KEY(id ASC) );
CREATE UNIQUE INDEX headers ON episodes(feed, title);
CREATE INDEX published_epoch ON episodes(published_epoch);

create table states_integer (name text, value integer,PRIMARY KEY(name asc));
create table states_text (name text, value text,PRIMARY KEY(name asc));
insert into states_integer(name,value) values('retrieve_episodes_epoch',1569277716);
