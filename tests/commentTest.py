import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import get_subreddit_posts, get_posts_comments, get_user, get_client
from utils import to_dict, save_json

reddit = get_client()

# Fetch one post from a popular, SFW subreddit
posts = get_subreddit_posts('python', num_posts=1, sort_by='hot')
assert posts, 'No posts fetched.'

save_json(to_dict(posts), 'tests/post_output.json')

# Fetch comments for the post
comments = get_posts_comments(posts, days_back=9999)
assert isinstance(comments, list), 'Comments not a list.'
if comments:
    comment_dicts = to_dict(comments)
    assert isinstance(comment_dicts, list), 'Comment to_dict failed.'
    save_json(comment_dicts, 'tests/comment_output.json')
    # Get the author of the first comment
    author = comments[0].author
    if author:
        user = get_user(reddit, author)
        if user:
            user_dicts = to_dict(user)
            assert isinstance(user_dicts, list), 'User to_dict failed.'
            save_json(user_dicts, 'tests/user_output.json')
        else:
            print('User object could not be fetched.')
    else:
        print('Comment has no author.')
else:
    print('No comments found for the post.')

print('Test completed. JSON files saved in tests/.')
