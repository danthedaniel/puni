import os
import random
import json

import praw
from puni import UserNotes, Note

# Read in config file
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'oauth.json'))
config = json.loads(open(config_path, 'r').read())
config['user_agent'] = 'puni nosetests'

# Instantiate Reddit and Subreddit objects
r = praw.Reddit(**config)
my_sub = r.subreddit('teaearlgraycold')


def test_init_notes():
    """Assert that the puni init_notes function sends new JSON to the wiki page"""

    un = UserNotes(r, my_sub)
    un.init_notes()
    stored_json = un.get_json()
    moderators = [x.name for x in my_sub.moderator()]

    assert stored_json['ver'] == un.schema
    assert stored_json['users'] == {}
    assert stored_json['constants']['users'] == moderators
    assert stored_json['constants']['warnings'] == Note.warnings


def test_add_note():
    """Assert that notes are added to the usernotes wiki page"""
    un = UserNotes(r, my_sub, lazy_start=True)

    note_message = "test note {}".format(random.random())
    new_note = Note("teaearlgraycold", note_message, warning='gooduser')

    un.add_note(new_note)
    stored_json = un.get_json()

    for note in stored_json['users']['teaearlgraycold']['ns']:
        if note['n'] == note_message:
            break
    else:
        assert False  # Did not reach a note with the sent message


def test_get_notes():
    """Assert that the puni get_notes function returns a list of Note objects"""
    un = UserNotes(r, my_sub, lazy_start=True)
    tea_notes = un.get_notes('teaearlgraycold')

    assert isinstance(tea_notes, list)
    assert isinstance(tea_notes[0], Note)


def test_remove_note():
    """Assert that notes are removed from the usernotes wiki page"""
    un = UserNotes(r, my_sub, lazy_start=True)
    un.remove_note('teaearlgraycold', 0)

    try:
        # teaearlgraycold should have no notes, and no entry whatsoever
        un.cached_json['users']['teaearlgraycold']
        assert False
    except KeyError:
        pass
