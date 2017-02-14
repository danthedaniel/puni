# puni - Python UserNotes Interface for Reddit
# Author: teaearlgraycold

"""
Contains two classes, Note and UserNotes. The Note class is used when de-
serializing the JSON notes from reddit, and should be the only interface used
when reading from/writing to the usernotes wiki page.

The UserNotes class is instantiated and used to manage the usernotes cache and
serialization/deserialization.
"""


import json
import time
import re
import zlib
import base64
import copy

from prawcore.exceptions import NotFound
from puni.decorators import update_cache


class Note(object):
    """Class that represents an individual usernote"""

    warnings = [
        'none',
        'spamwatch',
        'spamwarn',
        'abusewarn',
        'ban',
        'permban',
        'botban',
        'gooduser'
    ]

    def __init__(self, user, note, subreddit=None, mod=None, link='',
                 warning='none', note_time=int(time.time())):
        """
        Constuctor for the Note class.

        Arguments:
            user: the username of the user the note is attached to (str)
            note: the message attached to the note (str)
            subreddit: the subreddit the note comes from (str)
            mod: the username of the moderator that created the note (str)
            link: the URL associated with the note (can be a full reddit URL or
                usernote's shorthand format)
            warning: the type of warning. must be in Note.warnings (str)
            time: a UNIX epoch timestamp in seconds (int)
        """
        self.username = user
        self.note = note
        self.subreddit = str(subreddit) if subreddit else None
        self.time = note_time
        self.moderator = mod

        # Compress link if necessary
        full_link_re = re.compile(r'^https?://(\w{1,3}\.)?reddit.com/')
        compr_link_re = re.compile(r'[ml],[A-Za-z\d]{2,}(,[A-Za-z\d]+)?')

        if full_link_re.match(link):
            self.link = Note.compress_url(link)
        elif compr_link_re.match(link):
            self.link = link
        else:
            self.link = ''

        if warning in Note.warnings:
            self.warning = warning
        else:
            self.warning = 'none'

    def __str__(self):
        return '{}: {}'.format(self.username, self.note)

    def __repr__(self):
        return 'Note(user_name=\'{}\')'.format(self.username)

    def full_url(self):
        """
        Returns the full reddit URL associated with the usernote.

        Arguments:
            subreddit: the subreddit name for the note (PRAW Subreddit object)
        """
        if self.link == '':
            return ''
        else:
            return Note.expand_url(self.link, self.subreddit)

    @staticmethod
    def compress_url(link):
        """
        Static method that converts a reddit URL for a post, comment, or message
        into the shorthand used by usernotes.

        Arguments:
            link: a link to a comment, submission, or message (str)

        Returns a String object of the shorthand URL
        """
        comment_re = re.compile(r'/comments/([A-Za-z\d]{2,})(?:/[^\s]+/([A-Za-z\d]+))?')
        message_re = re.compile(r'/message/messages/([A-Za-z\d]+)')

        matches = re.findall(comment_re, link)

        if len(matches) == 0:
            matches = re.findall(message_re, link)

            if len(matches) == 0:
                return None
            else:
                return 'm,' + matches[0]
        else:
            if matches[0][1] == '':
                return 'l,' + matches[0][0]
            else:
                return 'l,' + matches[0][0] + ',' + matches[0][1]

    @staticmethod
    def expand_url(short_link, subreddit=None):
        """
        Static method that converts a usernote's URL shorthand into a full reddit
        URL.

        Arguments:
            subreddit: the subreddit the URL is for (PRAW Subreddit object or str)
            short_link: the compressed link from a usernote (str)

        Returns a String object of the full URL.
        """
        # Some URL structures for notes
        message_scheme = 'https://reddit.com/message/messages/{}'
        comment_scheme = 'https://reddit.com/r/{}/comments/{}/-/{}'
        post_scheme = 'https://reddit.com/r/{}/comments/{}/'

        if short_link == '':
            return None
        else:
            parts = short_link.split(',')

            if parts[0] == 'm':
                return message_scheme.format(parts[1])
            if parts[0] == 'l' and subreddit:
                if len(parts) > 2:
                    return comment_scheme.format(subreddit, parts[1], parts[2])
                else:
                    return post_scheme.format(subreddit, parts[1])
            elif not subreddit:
                raise ValueError('Subreddit name must be provided')
            else:
                return None


class UserNotes(object):
    """Class that represents an entire usernotes wiki page"""

    schema = 6  # Supported schema version
    max_page_size = 524288  # Characters
    zlib_compression_strength = 9
    page_name = 'usernotes'

    def __init__(self, r, subreddit, lazy_start=False):
        """
        Constuctor for the UserNotes class.

        Arguments:
            r: the authenticated reddit instance (PRAW Reddit Object)
            subreddit: the subreddit the usernotes will be pulled from (PRAW
                Subreddit object)
        """
        self.r = r
        self.subreddit = subreddit
        self.cached_json = {}

        if not lazy_start:
            self.get_json()

    def __repr__(self):
        return "UserNotes(subreddit=\'{}\')".format(self.subreddit.display_name)

    def get_json(self):
        """
        Get the JSON stored on the usernotes wiki page.

        Returns a Dict representation of the usernotes (with the notes BLOB
        decoded).

        Raises:
            praw.errors.Forbidden if the authenticated reddit session does not have
            permission to access the wiki page.
            praw.errors.HTTPException if an HTTP error code besides 404 returns.
        """

        try:
            usernotes = self.subreddit.wiki[self.page_name].content_md
            notes = json.loads(usernotes)
        except NotFound:
            self.init_notes()
        else:
            if notes['ver'] != self.schema:
                raise RuntimeError(
                    'Usernotes schema is v{0}, puni requires v{1}'.
                    format(notes['ver'], self.schema)
                )

            self.cached_json = self.expand_json(notes)

        return self.cached_json

    def init_notes(self):
        """
        Sets up the UserNotes page with the initial JSON schema
        """
        self.cached_json = {
            'ver': self.schema,
            'users': {},
            'constants': {
                'users': [x.name for x in self.subreddit.moderator()],
                'warnings': Note.warnings
            }
        }

        self.set_json('Initializing JSON via puni', True)

    def set_json(self, reason='', new_page=False):
        """
        Sends the JSON from the cache to the usernotes wiki page

        Arguments:
            reason: the change reason that will be posted to the wiki changelog
                (String)
        Raises:
            praw.errors.Forbidden if the authenticated reddit session does not have
            permission to access the wiki page.
            praw.errors.HTTPException if an HTTP error code besides 404 returns.
        """
        compressed_json = self.compress_json(self.cached_json)

        if len(compressed_json) > self.max_page_size:
            raise OverflowError(
                'Usernotes page is too large (>{0} characters)'.
                format(self.max_page_size)
            )

        if new_page:
            self.subreddit.wiki.create(
                self.page_name,
                json.dumps(compressed_json),
                reason
            )
            # Set the page as hidden and available to moderators only
            self.subreddit.wiki[self.page_name].mod.update(False, permlevel=2)
        else:
            self.subreddit.wiki[self.page_name].edit(
                json.dumps(compressed_json),
                reason
            )

    @update_cache
    def get_notes(self, user):
        """
        Arguments:
            user: the user to search for in the usernotes (String)

        Returns a list of Note objects for the given user
        """
        # Try to search for all notes on a user, return an empty list if none
        # are found.
        try:
            users_notes = []

            for note in self.cached_json['users'][user]['ns']:
                users_notes.append(Note(
                    user=user,
                    note=note['n'],
                    subreddit=self.subreddit,
                    mod=self.mod_from_index(note['m']),
                    link=note['l'],
                    warning=self.warning_from_index(note['w']),
                    note_time=note['t']
                ))

            return users_notes
        except KeyError:
            return []

    @update_cache
    def get_users(self):
        """
        Returns a list of all users with notes
        """
        return list(self.cached_json['users'].keys())

    def mod_from_index(self, index):
        """
        Arguments:
           index: the index in the constants array for moderators

        Returns the moderator name as a string
        """
        return self.cached_json['constants']['users'][index]

    def warning_from_index(self, index):
        """
        Arguments:
           index: the index in the constants array for warning

        Returns the warning as a string
        """
        return self.cached_json['constants']['warnings'][index]

    def expand_json(self, j):
        """
        Decompress the BLOB portion of the usernotes

        Arguments:
            j: the JSON returned from the wiki page (Dict)

        Returns a Dict with the 'blob' key removed and a 'users' key added
        """
        decompressed_json = copy.copy(j)
        decompressed_json.pop('blob', None)  # Remove BLOB portion of JSON

        # Decode and decompress JSON
        compressed_data = base64.b64decode(j['blob'])
        original_json = zlib.decompress(compressed_data).decode('utf-8')

        decompressed_json['users'] = json.loads(original_json)  # Insert users

        return decompressed_json

    def compress_json(self, j):
        """
        Compress the BLOB data portion of the usernotes

        Arguments:
            j: the JSON in Schema v5 format

        Returns a dict with the 'users' key removed and 'blob' key added
        """
        compressed_json = copy.copy(j)
        compressed_json.pop('users', None)

        compressed_data = zlib.compress(
            json.dumps(j['users']).encode('utf-8'),
            self.zlib_compression_strength
        )
        b64_data = base64.b64encode(compressed_data).decode('utf-8')

        compressed_json['blob'] = b64_data

        return compressed_json

    @update_cache
    def add_note(self, note):
        """
        Adds a note to the usernotes wiki page

        Arguments:
            note: the note to be added (Note)

        Returns the update message for the usernotes wiki

        Raises:
            ValueError when the warning type of the note can not be found in the
            stored list of warnings.
        """
        notes = self.cached_json

        if not note.moderator:
            note.moderator = self.r.user.me().name

        # Get index of moderator in mod list from usernotes
        # Add moderator to list if not already there
        try:
            mod_index = notes['constants']['users'].index(note.moderator)
        except ValueError:
            notes['constants']['users'].append(note.moderator)
            mod_index = notes['constants']['users'].index(note.moderator)

        # Get index of warning type from warnings list
        # Add warning type to list if not already there
        try:
            warn_index = notes['constants']['warnings'].index(note.warning)
        except ValueError:
            if note.warning in Note.warnings:
                notes['constants']['warnings'].append(note.warning)
                warn_index = notes['constants']['warnings'].index(note.warning)
            else:
                raise TypeError('Warning type not valid: ' + note.warning)

        new_note = {
            'n': note.note,
            't': note.time,
            'm': mod_index,
            'l': note.link,
            'w': warn_index
        }

        try:
            notes['users'][note.username]['ns'].insert(0, new_note)
        except KeyError:
            notes['users'][note.username] = {}
            notes['users'][note.username]['ns'] = []
            notes['users'][note.username]['ns'].append(new_note)

        return '"create new note on user {}" via puni'.format(note.username)

    @update_cache
    def remove_note(self, username, index):
        """
        Remove a single usernote from the usernotes

        Arguments:
            username: the user that for whom you're removing a note (str)
            index: the index of the note which is to be removed (int)

        Returns the update message for the usernotes wiki
        """
        self.cached_json['users'][username]['ns'].pop(index)

        # Go ahead and remove the user's entry if they have no more notes left
        if len(self.cached_json['users'][username]['ns']) == 0:
            del self.cached_json['users'][username]

        return '"delete note #{} on user {}" via puni'.format(index, username)

    @update_cache
    def remove_user(self, username):
        """
        Remove all of a user's notes

        Arguments:
            username: the user to have its notes removed (str)

        Returns the update message for the usernotes wiki
        """
        del self.cached_json['users'][username]
        return '"delete user {} from usernotes" via puni'.format(username)
