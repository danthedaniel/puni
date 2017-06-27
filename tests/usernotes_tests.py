import os
import random
import praw
from puni import UserNotes, Note, __version__


# Instantiate Reddit and Subreddit objects
r = praw.Reddit(
    client_id=os.environ['CLIENT_ID'],
    client_secret=os.environ['CLIENT_SECRET'],
    username=os.environ['USERNAME'],
    password=os.environ['PASSWORD'],
    user_agent='puni v{} nosetests by teaearlgraycold'.format(__version__)
)
my_sub = r.subreddit('teaearlgraycold')


def test_init_notes():
    """Assert that the puni init_notes function sends new JSON to the wiki page."""
    un = UserNotes(r, my_sub)
    un._init_notes()
    stored_json = un.get_json()
    moderators = [x.name for x in my_sub.moderator()]

    assert stored_json['ver'] == un.schema
    assert stored_json['users'] == {}
    assert stored_json['constants']['users'] == moderators
    assert stored_json['constants']['warnings'] == Note.warnings


def test_add_note():
    """Assert that notes are added to the usernotes wiki page."""
    un = UserNotes(r, my_sub, lazy_start=True)
    note_message = 'test note {}'.format(random.random())
    new_note = Note('teaearlgraycold', note_message, warning='gooduser')
    un.add_note(new_note)
    stored_json = un.get_json()
    messages = {x['n'] for x in stored_json['users']['teaearlgraycold']['ns']}

    assert note_message in messages


def test_get_notes():
    """Assert that the puni get_notes function returns a list of Note objects."""
    un = UserNotes(r, my_sub, lazy_start=True)
    tea_notes = un.get_notes('teaearlgraycold')

    assert isinstance(tea_notes, list)
    assert isinstance(tea_notes[0], Note)


def test_remove_user():
    """Assert that all user's notes are removed from the usernotes wiki page."""
    un = UserNotes(r, my_sub, lazy_start=True)
    un.remove_user('teaearlgraycold')

    assert un.cached_json['users'].get('teaearlgraycold') is None


def test_lazy_add_note():
    """Assert that the add_note method will not affect the wiki page contents when lazy."""
    un = UserNotes(r, my_sub)
    un2 = UserNotes(r, my_sub, lazy_start=True)
    new_note = Note('foobar', 'foobar note', warning='gooduser')
    un.add_note(new_note, lazy=True)

    assert 'foobar' in un.get_users(lazy=True)
    assert 'foobar' not in un2.get_users()
