import praw
from puni import Note

r = praw.Reddit('puni nosetests')


def test_note():
    """Ensure Note class compresses URL for messages"""
    n = Note(
        user='teaearlgraycold',
        note='creator of puni',
        subreddit='teaearlgraycold',
        mod='teaearlgraycold',
        link='https://reddit.com/message/messages/000fff',
        warning='gooduser'
    )

    assert n.link == 'm,000fff'
    assert n.full_url() == 'https://reddit.com/message/messages/000fff'


def test_note_2():
    """Ensure Note class compresses URL for submissions"""
    n = Note(
        user='teaearlgraycold',
        note='creator of puni',
        subreddit='pics',
        mod='teaearlgraycold',
        link='https://www.reddit.com/r/pics/comments/92dd8/test_post_please_ignore',
        warning='gooduser'
    )

    assert n.link == 'l,92dd8'
    assert n.full_url() == 'https://reddit.com/r/pics/comments/92dd8/'


def test_note_3():
    """Ensure Note class compresses URL for comments"""
    n = Note(
        user='teaearlgraycold',
        note='creator of puni',
        subreddit='pics',
        mod='teaearlgraycold',
        link='https://www.reddit.com/r/pics/comments/92dd8/test_post_please_ignore/c0b6xx0',
        warning='gooduser'
    )

    assert n.link == 'l,92dd8,c0b6xx0'
    assert n.full_url() == 'https://reddit.com/r/pics/comments/92dd8/-/c0b6xx0'


def test_note_4():
    """Ensure Note class throws exception when expanding a url without a specified subreddit"""
    n = Note(
        user='teaearlgraycold',
        note='creator of puni',
        mod='teaearlgraycold',
        link='https://www.reddit.com/r/pics/comments/92dd8/test_post_please_ignore/c0b6xx0',
        warning='gooduser'
    )

    try:
        n.full_url()
        assert False
    except ValueError:
        pass
