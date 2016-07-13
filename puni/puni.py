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

from requests.exceptions import HTTPError
from .exceptions import ServerResponseError, PermissionError
from .decorators import update_cache


class Note:
    warnings = ['none', 'spamwatch', 'spamwarn', 'abusewarn', 'ban', 'permban', 'botban', 'gooduser']

    def __init__(self, user, note, mod=None, link='', warning='none', time=int(time.time())):
        """
        Constuctor for the Note class.

        Arguments:
            user: the username of the user the note is attached to (String)
            note: the message attached to the note (String)
            mod: the username of the moderator that created the note (String)
            link: the URL associated with the note (can be a full reddit URL or
                usernote's shorthand format)
            warning: the type of warning. must be in Note.warnings (String)
            time: a UNIX epoch timestamp in seconds (Integer)
        """
        self.username = user

        self.note = note
        self.time = time
        self.moderator = mod

        # Compress link if necessary
        self.full_link_re = re.compile(r'^https?://(\w{1,3}\.)?reddit.com/')
        self.compr_link_re = re.compile(r'[ml],[A-Za-z\d]{6}(,[A-Za-z\d]{7})?')

        if self.full_link_re.match(link):
            self.link = Note.compress_url(link)
        elif self.compr_link_re.match(link):
            self.link = link
        else:
            self.link = ''

        if warning in Note.warnings:
            self.warning = warning
        else:
            self.warning = 'none'

    def __str__(self):
        return "{}: {} by {}".format(self.username, self.note, self.moderator)

    def __repr__(self):
        return "Note(user_name=\'{}\')".format(self.username)

    def full_url(self, subreddit=None):
        """
        Returns the full reddit URL associated with the usernote.

        Arguments:
            subreddit: the subreddit name for the note (PRAW Subreddit object)
        """
        if self.link == '':
            return ''
        else:
            return Note.expand_url(self.link, subreddit)

    @staticmethod
    def compress_url(link):
        """
        Static method that converts a reddit URL for a post, comment, or message
        into the shorthand used by usernotes.

        Arguments:
            link: a link to a comment, submission, or message

        Returns a String object of the shorthand URL
        """
        comments = re.compile(r'/comments/([A-Za-z\d]{2,})(?:/[^\s]+/([A-Za-z\d]+))?')
        messages = re.compile(r'/message/messages/([A-Za-z\d]+)')

        matches = re.findall(comments, link)

        if len(matches) == 0:
            matches = re.findall(messages, link)

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
            subreddit: the subreddit the URL is for (PRAW Subreddit object)
            short_link: the compressed link from a usernote (String)

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
                    return comment_scheme.format(subreddit.display_name, parts[1], parts[2])
                else:
                    return post_scheme.format(subreddit.display_name, parts[1])
            elif not subreddit:
                raise ValueError('Subreddit name must be provided')
            else:
                return None


class UserNotes:
    def __init__(self, r, subreddit):
        """
        Constuctor for the UserNotes class.

        Arguments:
            r: the authenticated reddit instance (PRAW Reddit Object)
            subreddit: the subreddit the usernotes will be pulled from (PRAW
                Subreddit object)
        """
        self.r = r
        self.subreddit = subreddit

        # Supported schema version
        self.schema = 6

        self.max_page_size = 524288  # Characters
        self.cache_timeout = 5
        self.last_visited = 0
        self.num_retries = 2
        self.page_name = 'usernotes'
        self.cached_json = self.get_json()

    def __repr__(self):
        return "UserNotes(subreddit=\'{}\')".format(self.subreddit.display_nanme)

    def get_json(self, attempts=None):
        """
        Get either new JSON from the wiki page or return the cached JSON if less
        than the number of seconds defined in self.cache_timeout have passed.

        Arguments:
            attempts: the number of HTTP requests to make if reddit returns a
                500 error code. Will default to the value of self.num_retries
                (Integer)

        Returns a Dict representation of the usernotes (with the notes BLOB
        decoded).

        Throws:
            PermissionError if the authenticated reddit session does not have
            permission to access the wiki page.
            HTTPError if an HTTP error code besides 403, 404, 502..504 returns.
            ServerResponseError if the method exceeds its maximum retry count.
        """
        if not attempts:
            attempts = self.num_retries

        # Gets most recent version of usernotes unless cache timeout is still
        # active in which case returns the cached usernotes
        if (time.time() - self.last_visited) > self.cache_timeout:
            self.last_visited = time.time()

            # HTTPError handling
            # If a 403 error - throw a PermissionError
            # If a 404 error - create the wiki page
            # If a 502,503,504 error - retry
            # Otherwise, re-throw the exception
            try:
                usernotes = self.r.get_wiki_page(self.subreddit, self.page_name)

            except HTTPError as e:
                if e.response.status_code == 403:
                    raise PermissionError('puni needs the wiki permission to read usernotes')

                # Initializes usernotes with barebones JSON
                elif e.response.status_code == 404:
                    temp_json = {
                        'ver': self.schema,
                        'users': [],
                        'constants': {
                            'users': [x.name for x in self.subreddit.get_moderators()],
                            'warnings': Note.warnings
                        }
                    }

                    self.set_json(temp_json, 'Initializing JSON via puni')

                    return temp_json

                elif e.response.status_code in [502, 503, 504]:
                    if attempts != 0:
                        return self.get_json(attempts - 1)
                    else:
                        try:
                            return self.cached_json
                        except NameError:
                            raise ServerResponseError('Could not get initial JSON')

                else:
                    raise e

            try:
                # Remove XML entities and convert into a dict
                notes = json.loads(usernotes.content_md)
            except ValueError:
                return None

            if notes['ver'] != self.schema:
                raise AssertionError('Schema must be v{}'.format(self.schema))

            # Make sure to decompress before returning
            decompressed_notes = self.expand_json(notes)

            self.cached_json = decompressed_notes
            return decompressed_notes
        else:
            return self.cached_json

    def set_json(self, reason, attempts=None):
        """
        Sends new JSON from the cache to be written to the usernotes wiki page.

        Arguments:
            reason: the change reason that will be posted to the wiki changelog
                (String)
            attempts: the number of HTTP requests to make if reddit returns a
                500 error code. Will default to the value of self.num_retries
                (Integer)

        Throws:
            PermissionError if the authenticated reddit session does not have
            permission to access the wiki page.
            HTTPError if an HTTP error code besides 403, 404, 502..504 returns.
            ServerResponseError if the method exceeds its maximum retry count.
        """
        if not attempts:
            attempts = self.num_retries

        if not reason:
            reason = ''

        notes = self.cached_json

        try:
            compressed_json = self.compress_json(notes)

            if len(compressed_json) <= self.max_page_size:
                self.r.edit_wiki_page(self.subreddit, self.page_name, json.dumps(compressed_json), reason)
            else:
                raise ValueError('Usernotes page is too large (>{} characters)'.
                    format(self.max_page_size))

        except HTTPError as e:
            if e.response.status_code == 403:
                PermissionError('puni needs the wiki permission to write to usernotes')

            elif e.response.status_code in [502, 503, 504]:
                if attempts != 0:
                    self.set_json(notes, reason, attempts - 1)
                elif attempts == 0:
                    raise ServerResponseError('No response while writing usernotes')

            else:
                raise e

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
                    mod=self.mod_from_index(note['m']),
                    link=note['l'],
                    warning=self.warning_from_index(note['w'])
                ))

            return users_notes
        except KeyError:
            return []

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

        compressed_data = zlib.compress(json.dumps(j['users']).encode('utf-8'))
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

        Throws:
            ValueError when the warning type of the note can not be found in the
            stored list of warnings.
        """
        notes = self.cached_json

        if not note.moderator:
            note.moderator = self.r.user.name

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
                raise ValueError('Warning type not valid: ' + note.warning)

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
            username: the user that for whom you're removing a note (String)
            index: the index of the note which is to be removed (Integer)

        Returns the update message for the usernotes wiki
        """
        self.cached_json['users'][username]['ns'].pop(index)
        return '"delete note #{} on user {}" via puni'.format(index, username)
