import sqlite3
import click
from flask import current_app, g, request
from flask.cli import with_appcontext

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config['DATABASE'])
    return db

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    get_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_connection)
    app.cli.add_command(init_db_command)

def close_connection(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

site_data_query = (
    "CREATE TABLE IF NOT EXISTS sitedata "
    "(sitename TEXT NOT NULL," 
    "main_address TEXT NOT NULL,"
    "scrape_address TEXT NOT NULL,"
    "sitetype TEXT NOT NULL,"
    "list_query TEXT NOT NULL,"
    "link_query TEXT NOT NULL,"
    "postnum_query INTEGER NOT NULL,"
    "title_query TEXT NOT NULL,"
    "author_query TEXT NOT NULL,"
    "js_included INTEGER)")

site_feed_query = (
    "CREATE TABLE IF NOT EXISTS sitefeed "
    "(ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,"
    "sitename TEXT NOT NULL," 
    "sitetype TEXT NOT NULL,"
    "postdate TEXT NOT NULL,"
    "postnum INTEGER NOT NULL,"
    "title TEXT NOT NULL,"
    "author TEXT NOT NULL,"
    "link TEXT NOT NULL)")

insert_feed_query = (
    "INSERT INTO sitefeed "
    "(sitename, sitetype, postdate, postnum, title, author, link) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)