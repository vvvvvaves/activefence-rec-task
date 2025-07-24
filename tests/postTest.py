import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import get_subreddit_posts, get_client
from utils import to_dict, save_json

reddit = get_client()

# Fetch multiple posts from a popular, SFW subreddit
posts = get_subreddit_posts('python', num_posts=5, sort_by='hot')
assert posts, 'No posts fetched.'

# Convert posts to dict and save as JSON
post_dicts = to_dict(posts)
assert isinstance(post_dicts, list) and post_dicts, 'Post to_dict failed.'
save_json(post_dicts, 'tests/post_output.json')

print('Post test completed. JSON file saved in tests/post_output.json')
