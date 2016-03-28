PUNI
===

Python UserNotes Interface for Reddit.

Built to interact with the user notes data store from the reddit moderator
toolbox

**Requirements**:
* [PRAW](https://github.com/praw-dev/praw)
* Python 3.X
* user must have wiki permissions on the subreddit and bot must be given the
proper OAuth scopes

*Note*: PUNI only supports usernotes of schema version 6.

**Usage**:

*Creating a usernotes object*

```python
# First, define r as an authenticated PRAW Reddit instance
sub = r.get_subreddit('subreddit')

un = puni.UserNotes(r, sub)
```

*Adding a note*

```python
#Create given note with time set to current time
link = 'http://www.reddit.com/message/messages/4vjx3v'
n = puni.Note('username','reason','moderator',link,'permban')
un.add_note(n)
```

The list of warning types (like `'permban'` as shown above), can be accessed from
`puni.Note.warnings`.

*Reading a user's notes*

```python
for note in un.get_notes('username'):
    print(note.note)
```
