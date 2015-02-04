#PUNI
Python UserNotes Interface for Reddit

Requirements:
* praw
* Python 3.4
* user must have wiki permissions on the subreddit

Usage:

*Creating a usernotes object*

    r = praw.Reddit(user_agent='teaearlgraycold via IDLE')
    r.login('username', 'password')
    sub = r.get_subreddit('subreddit')

    un = puni.UserNotes(r, sub)
    
*Adding a note*

    link = puni.compress_url('http://www.reddit.com/message/messages/4vjx3v')
    n = puni.Note('username','my key',int(time.time()*1000),'moderator',link,'permban')
    un.add_note(n)

*Reading a user's notes*

    notes = un.get_notes('username')
    
    for note in notes:
        print(note.note)
