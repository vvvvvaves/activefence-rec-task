import praw
import os
from dotenv import load_dotenv
import json
from utils import get_targeting_data, to_dict
import random
from datetime import datetime, timedelta, timezone
from typing import Generator
import prawcore
load_dotenv()
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
USERNAME = os.getenv('REDDIT_USERNAME')
USER_AGENT = f'script:afrt:v1.0 (by u/{USERNAME})'

def get_client() -> praw.Reddit:
    """
    Create and return a Reddit client instance using PRAW and environment variables.
    
    Input:
        None (uses environment variables REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, USER_AGENT)
    Output:
        praw.Reddit: An authenticated Reddit client instance.
    """
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=USER_AGENT
    )
    reddit.config.log_requests = 1
    reddit.config.store_json_result = True
    return reddit


def get_subreddit_posts(
    client,
    subreddit_name, 
    num_posts=10, 
    sort_by='hot', 
    days_back=9999
    ) -> Generator[praw.models.Submission, None, None]:
    """
    Fetch posts from a subreddit with sorting option and optional days_back filter.
    Only fetches and filters posts; does not do any metrics or preprocessing.
    
    Input:
        subreddit_name (str): Name of the subreddit (e.g., 'python').
        num_posts (int, optional): Number of posts to fetch. Default is 10.
        sort_by (str, optional): Sorting method. One of 'hot', 'new', 'top', 'rising'. Default is 'hot'.
        days_back (int, optional): If provided, only posts from the last 'days_back' days are returned. Default is None (no filter).
    Output:
        list of praw.models.Submission: List of Reddit post objects matching the criteria.
    """
    subreddit = client.subreddit(subreddit_name)
    if sort_by == 'hot':
        posts = subreddit.hot(limit=num_posts)
    elif sort_by == 'new':
        posts = subreddit.new(limit=num_posts)
    elif sort_by == 'top':
        posts = subreddit.top(limit=num_posts)
    elif sort_by == 'rising':
        posts = subreddit.rising(limit=num_posts)
    else:
        raise ValueError("Invalid sort_by value. Use 'hot', 'new', 'top', or 'rising'.")
    
    cutoff_date = None
    if days_back is not None:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    try:
        for post in posts:
            post_date = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            if cutoff_date is None or post_date >= cutoff_date:
                yield post
    except prawcore.exceptions.NotFound:
        return []

def search_reddit_posts(
    client,
    query, 
    num_posts=10, 
    sort_by='relevance'
    ) -> Generator[praw.models.Submission, None, None]:
    """
    Search Reddit posts across all subreddits using a query string.
    
    Input:
        query (str): Search query string.
        num_posts (int, optional): Number of posts to return. Default is 10.
        sort_by (str, optional): Sorting method. One of 'relevance', 'hot', 'top', 'new', 'comments'. Default is 'relevance'.
    Output:
        list of praw.models.Submission: List of Reddit post objects matching the search.
    """
    results = client.subreddit('all').search(query, sort=sort_by, limit=num_posts)
    try:
        for result in results:
            yield result
    except prawcore.exceptions.NotFound:
        return []

def search_subreddit_posts(
    client,
    subreddit_name, 
    query, 
    num_posts=10, 
    days_back=9999, 
    sort_by='relevance', 
    save_query=False,
    ) -> Generator[praw.models.Submission, None, None]:
    """
    Search posts within a specific subreddit using a query string.
    
    Input:
        subreddit_name (str): Name of the subreddit (e.g., 'python').
        query (str): Search query string.
        num_posts (int, optional): Number of posts to return. Default is 10.
        sort_by (str, optional): Sorting method. One of 'relevance', 'hot', 'top', 'new', 'comments'. Default is 'relevance'.
    Output:
        list of praw.models.Submission: List of Reddit post objects matching the search.
    """
    subreddit = client.subreddit(subreddit_name)
    results = subreddit.search(query, sort=sort_by, limit=num_posts, time_filter='all')
    cutoff_date = None
    if days_back is not None:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    try:
        for result in results:
            result_date = datetime.fromtimestamp(result.created_utc, tz=timezone.utc)
            if cutoff_date is None or result_date >= cutoff_date:
                if save_query:
                    yield result, query
                else:
                    yield result, None
    except prawcore.exceptions.NotFound:
        return []

    
def get_posts_comments(
    client,
    posts, 
    days_back=9999
    ) -> Generator[praw.models.Comment, None, None]:
    """
    Fetch raw comment objects for a given post or list of posts, filtered by days_back.
    
    Input:
        posts (praw.models.Submission or Generator[praw.models.Submission, None, None]): Single post object or list of post objects.
        days_back (int, optional): Only comments from the last 'days_back' days are returned. Default is 30.
    Output:
        list of praw.models.Comment: List of raw Reddit comment objects (not processed dicts) matching the filter.
    """
    if not isinstance(posts, Generator):
        posts = [posts]

    for post in posts:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        try:
            # Limit comment expansion to prevent hanging on posts with many comments
            # Only expand up to 10 "more comments" links to avoid excessive API calls
            post.comments.replace_more(limit=10)
            _comments = post.comments.list()
            try:
                for comment in _comments:
                    if isinstance(comment, praw.models.MoreComments):
                        continue
                    comment_date = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)
                    if comment_date < cutoff_date:
                        continue
                    else:
                        yield comment
            except prawcore.exceptions.NotFound:
                continue
        except Exception as e:
            print(f"Error processing comments for post {post.id}: {e}")
            return []

def get_user(
    client, 
    username
    ) -> praw.models.Redditor:
    """
    Fetch a Reddit user object using PRAW.
    
    Input:
        username (str): The Reddit username to fetch.
    Output:
        praw.models.Redditor: The Reddit user object.
    """
    try:
        user = client.redditor(username)
        # Optionally, trigger a fetch to ensure the user exists (raises exception if not)
        _ = user.id
        return user
    except Exception as e:
        print(f"Error fetching user '{username}': {e}")
        return None


def get_user_posts(
    client,
    user, 
    num_posts=10, 
    sort_by='new'
    ) -> Generator[praw.models.Submission, None, None]:
    """
    Fetch posts (submissions) made by a Reddit user.
    
    Input:
        user (praw.models.Redditor): The Reddit user object.
        num_posts (int, optional): Number of posts to fetch. Default is 10.
        sort_by (str, optional): Sorting method. One of 'new', 'hot', 'top', 'controversial'. Default is 'new'.
    Output:
        list of praw.models.Submission: List of Reddit post objects submitted by the user.
    """
    if sort_by == 'new':
        posts = user.submissions.new(limit=num_posts)
    elif sort_by == 'hot':
        posts = user.submissions.hot(limit=num_posts)
    elif sort_by == 'top':
        posts = user.submissions.top(limit=num_posts)
    elif sort_by == 'controversial':
        posts = user.submissions.controversial(limit=num_posts)
    else:
        raise ValueError("Invalid sort_by value. Use 'new', 'hot', 'top', or 'controversial'.")
    try:    
        for post in posts:
            yield post
    except prawcore.exceptions.NotFound:
        return []


def get_user_posts(
    client,
    user,
    num_posts=10,
    sort_by='new',
    days_back=None
) -> Generator[praw.models.Submission, None, None]:
    """
    Fetch posts (submissions) made by a Reddit user, with an optional cutoff date filter.
    
    Input:
        client: praw.Reddit client instance.
        user: Reddit username (str) or praw.models.Redditor object.
        num_posts (int, optional): Number of posts to fetch. Default is 10.
        sort_by (str, optional): Sorting method. One of 'new', 'hot', 'top', 'controversial'. Default is 'new'.
        days_back (int, optional): Only posts from the last 'days_back' days are returned. Default is None (no filter).
    Output:
        Generator[praw.models.Submission, None, None]: Reddit post objects submitted by the user, filtered by cutoff date if provided.
    """
    if isinstance(user, str):
        user = get_user(client, user)
        if user is None:
            return
    if sort_by == 'new':
        posts = user.submissions.new(limit=num_posts)
    elif sort_by == 'hot':
        posts = user.submissions.hot(limit=num_posts)
    elif sort_by == 'top':
        posts = user.submissions.top(limit=num_posts)
    elif sort_by == 'controversial':
        posts = user.submissions.controversial(limit=num_posts)
    else:
        raise ValueError("Invalid sort_by value. Use 'new', 'hot', 'top', or 'controversial'.")
    cutoff_date = None
    if days_back is not None:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    try:
        for post in posts:
            post_date = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            if cutoff_date is None or post_date >= cutoff_date:
                yield post
    except prawcore.exceptions.NotFound:
        return []


def get_user_comments(
    client,
    user,
    num_comments=10,
    sort_by='new',
    days_back=None
) -> Generator[praw.models.Comment, None, None]:
    """
    Fetch comments made by a Reddit user, with an optional cutoff date filter.
    
    Input:
        client: praw.Reddit client instance.
        user: Reddit username (str) or praw.models.Redditor object.
        num_comments (int, optional): Number of comments to fetch. Default is 10.
        sort_by (str, optional): Sorting method. One of 'new', 'hot', 'top', 'controversial'. Default is 'new'.
        days_back (int, optional): Only comments from the last 'days_back' days are returned. Default is None (no filter).
    Output:
        Generator[praw.models.Comment, None, None]: Reddit comment objects made by the user, filtered by cutoff date if provided.
    """
    if isinstance(user, str):
        user = get_user(client, user)
        if user is None:
            return
    if sort_by == 'new':
        comments = user.comments.new(limit=num_comments)
    elif sort_by == 'hot':
        comments = user.comments.hot(limit=num_comments)
    elif sort_by == 'top':
        comments = user.comments.top(limit=num_comments)
    elif sort_by == 'controversial':
        comments = user.comments.controversial(limit=num_comments)
    else:
        raise ValueError("Invalid sort_by value. Use 'new', 'hot', 'top', or 'controversial'.")
    cutoff_date = None
    if days_back is not None:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    try:
        for comment in comments:
            comment_date = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)
            if cutoff_date is None or comment_date >= cutoff_date:
                yield comment
    except prawcore.exceptions.NotFound:
        return []


if __name__ == "__main__":
    client = get_client()
    username = "DaftVapour"
    print(f"Testing get_user_posts for user: {username}")
    posts = list(get_user_posts(client, username, num_posts=3, sort_by='new', days_back=30))
    print(f"Number of posts retrieved: {len(posts)}")
    for i, post in enumerate(posts, 1):
        print(f"Post {i}: {post.title} (created: {datetime.fromtimestamp(post.created_utc, tz=timezone.utc)})")

    print(f"\nTesting get_user_comments for user: {username}")
    comments = list(get_user_comments(client, username, num_comments=3, sort_by='new', days_back=30))
    print(f"Number of comments retrieved: {len(comments)}")
    for i, comment in enumerate(comments, 1):
        print(f"Comment {i}: {comment.body[:60]}... (created: {datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)})")
