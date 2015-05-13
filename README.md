#PUNI
Python UserNotes Interface for Reddit

Requirements:
* praw
* Python 3.4
* user must have wiki permissions on the subreddit

Usage:

*Creating a usernotes object*

    r = praw.Reddit(user_agent='useragent')
    r.login('username', 'password')
    sub = r.get_subreddit('subreddit')

    un = puni.UserNotes(r, sub)
    
*Adding a note*

    link = puni.compress_url('http://www.reddit.com/message/messages/4vjx3v')
    
    #Create given note with time set to current time
    n = puni.Note('username','reason','moderator',link,'permban')
    un.add_note(n)

*Reading a user's notes*
    
    for note in un.get_notes('username'):
        print(note.note)
