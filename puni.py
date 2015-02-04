import praw
import json
import time
import re
#from HTMLParser import HTMLParser

from requests.exceptions import HTTPError

warning_types = ['none','spamwatch','spamwarn','abusewarn','ban','permban','botban']

def compress_url(link):
    comments = re.compile(r'/comments/([A-Za-z\d]{6})/[^\s]+/([A-Za-z\d]{7})?')
    messages = re.compile(r'/message/messages/([A-Za-z\d]{6})')
    
    matches = re.findall(comments, link)
    
    if len(matches) == 0:
        matches = re.findall(messages, link)
        
        if len(matches) == 0:
            return ''
        else:
            return 'm,' + matches[0]
    else:
        if matches[0][1] == '':
            return 'l,' + matches[0][0]
        else:
            return 'l,' + matches[0][0] + ',' + matches[0][1]

def expand_url(note, subreddit):
    if note.link == '':
        return None
    else:
        parts = self.note.split(',')
        
        if parts[0] == 'm':
            return 'https://reddit.com/message/messages/' + parts[1]
        if parts[0] == 'l':
            if len(parts) > 2:
                return 'https://reddit.com/r/' + subreddit.display_name + '/comments/' + parts[1] + '/-/' + parts[2]
            else:
                return 'https://reddit.com/r/' + subreddit.display_name + '/comments/' + parts[1]
        else:
            return None

class Note:
    def __init__(self, username, note, time=int(time.time()*1000), moderator=None, link='', warning='none'):
        self.username = username

        global warning_types

        self.note = note
        self.time = time
        self.moderator = moderator
        self.link = link

        if warning in warning_types:
            self.warning = warning
        else:
            self.warning = 'none'
            
class UserNotes:
    def __init__(self, r, subreddit):
        self.r = r
        self.subreddit = subreddit

        #Supported schema version
        self.schema = 4

        global warning_types

        #self.parser = HTMLParser()

        self.cache_timeout = 0
        self.cached_json = self.get_json()

    def get_json(self):
        #Gets most recent version of usernotes unless cache timeout is still active
        #in which case returns the cached usernotes
        if (time.time() - self.cache_timeout) > self.r.config.cache_timeout + 1:
            self.cache_timeout = time.time()

            #HTTPError handling
            #If a 404 error - create the wiki page
            #If a 503 error - retry
            #Otherwise, re-throw the exception
            try:
                usernotes = self.r.get_wiki_page(self.subreddit, 'usernote')
            except HTTPError as e:
                if e.response.status_code == 404:
                    temp_moderators = self.subreddit.get_moderators()

                    #Initializes usernotes with barebones JSON
                    warning_types_string = str(warning_types).replace("\'", "\"") #Double quotes are necessary for valid JSON

                    temp_json = json.loads('{"ver":' + str(self.schema) + ',"users":{},"constants":{"users":[],"warnings":' + warning_types_string + '}}')
                    temp_json['constants']['users'] = [x.name for x in temp_moderators]

                    self.set_json(temp_json, 'Initializing JSON')

                    return temp_json

                elif e.response.status_code == 503:
                    return self.get_json()

                else:
                    raise e

            #unesc_usernotes = self.parser.unescape(usernotes.content_md)

            try:
                notes = json.loads(usernotes.content_md)
            except ValueError:
                return None

            if notes['ver'] != self.schema:
                raise AssertionError('Schema version not v' + str(self.schema))

            return notes
        else:
            return self.cached_json

    def set_json(self, notes, reason):
        if reason == None:
            reason = ''

        self.cached_json = notes
        self.r.edit_wiki_page(self.subreddit, 'usernotes', json.dumps(notes), reason)
        
    def get_notes(self, username):
        notes = self.get_json()

        try:
            return [Note(username, x['n'], x['t'], x['m'], x['l'], x['w']) for x in notes['users'][username]['ns']]
        except KeyError:
            return []

    def add_note(self, note):
        if note.moderator == None:
            note.moderator = self.r.user.name

        notes = self.get_json()

        #Get index of moderator in mod list from usernotes
        #Add moderator to list if not already there
        try:
            mod_index = notes['constants']['users'].index(note.moderator)
        except ValueError:
            notes['constants']['users'].append(note.moderator)
            mod_index = notes['constants']['users'].index(note.moderator)

        #Get index of warning type from warnings list
        #Add warning type to list if not already there
        try:
            warn_index = notes['constants']['warnings'].index(note.warning)
        except ValueError:
            if note.warning in warning_types:
                notes['constants']['warnings'].append(note.warning)
                warn_index = notes['constants']['warnings'].index(note.warning)
            else:
                raise ValueError('Warning type not valid: ' + note.warning)

        new_note = json.loads('{"n":"' + note.note + '","t":' + str(note.time) + ',"m":' + str(mod_index) + ',"l":"' + note.link + '","w":' + str(warn_index) + '}')

        try:
            notes['users'][note.username]['ns'].insert(0, new_note)
        except KeyError:
            notes['users'][note.username] = {}
            notes['users'][note.username]['ns'] = []
            notes['users'][note.username]['ns'].append(new_note)

        self.set_json(notes, '"create new note on user ' + note.username + '" via puni')

    def remove_note(self, index):
        notes = self.get_json()
        notes['users'][note.username]['ns'].pop(index)

        self.set_json(notes, '"delete note ' + note.time + ' on user ' + note.username + '" via puni')
