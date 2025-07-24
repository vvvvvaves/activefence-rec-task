import praw
import os
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USERNAME = os.getenv('USERNAME')

print(CLIENT_ID)
print(CLIENT_SECRET)
print(USERNAME)

# Replace these with your Reddit app credentials

USER_AGENT = f'script:afrt:v1.0 (by u/{USERNAME})'

# Create a Reddit instance
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)

# Specify the subreddit and number of posts
subreddit_name = 'python'
num_posts = 10

subreddit = reddit.subreddit(subreddit_name)

print(f"Top {num_posts} posts from r/{subreddit_name}:")
for post in subreddit.hot(limit=num_posts):
    print(f"Title: {post.title}\nScore: {post.score}\nURL: {post.url}\n---")
