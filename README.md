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

*Please read the contents of `puni/puni.py` to see all functions available through puni*

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

*Pruning shadowbanned and deleted users*

```python
import puni
import praw

r = praw.Reddit('puni user pruning by teaearlgraycold v0.1')
r.login('username', 'password', disable_warning=True)

sub = r.get_subreddit('my_subreddit')
un = puni.UserNotes(r, sub)

user_list = un.get_users()

for user in user_list:
    try:
        u = r.get_redditor(user, fetch=True)
    except:
        print("{} is shadowbanned/deleted".format(user))
        # User is shadowbanned or account is deleted
        # Normally you'd use un.remove_user(), but since we are making many
        # deletions, it's best to only make one API call for the final changes
        # once we're at the end of the script.
        del un.cached_json['users'][user]

# Now update the usernotes
un.set_json("Pruned users via puni")
```
