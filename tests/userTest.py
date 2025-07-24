import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import get_subreddit_posts, get_user, get_client
from utils import to_dict, save_json

reddit = get_client()

# Fetch one post from a popular, SFW subreddit
posts = get_subreddit_posts('python', num_posts=1, sort_by='hot')
assert posts, 'No posts fetched.'

# Get the author of the first post
post = posts[0]
author = post.author
assert author, 'Post has no author.'

# Fetch the user object
user = get_user(reddit, author.name)
assert user, 'User object could not be fetched.'

# Convert user to dict and save as JSON
user_dicts = to_dict(user)
assert isinstance(user_dicts, list) and user_dicts, 'User to_dict failed.'
save_json(user_dicts, 'tests/user_output.json')

print('User test completed. JSON file saved in tests/user_output.json')
