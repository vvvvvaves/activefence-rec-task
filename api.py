import praw
import os
from dotenv import load_dotenv
import json
from utils import get_targeting_data, to_dict
import random
from datetime import datetime, timedelta
from typing import Generator
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USERNAME = os.getenv('USERNAME')
USER_AGENT = f'script:afrt:v1.0 (by u/{USERNAME})'

def get_client() -> praw.Reddit:
    """
    Create and return a Reddit client instance using PRAW and environment variables.
    
    Input:
        None (uses environment variables CLIENT_ID, CLIENT_SECRET, USER_AGENT)
    Output:
        praw.Reddit: An authenticated Reddit client instance.
    """
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT
    )
    reddit.config.log_requests = 1
    reddit.config.store_json_result = True
    return reddit


reddit = get_client()

def get_subreddit_posts(
    subreddit_name, 
    num_posts=10, 
    sort_by='hot', 
    days_back=None
    ) -> list[praw.models.Submission]:
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
    subreddit = reddit.subreddit(subreddit_name)
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
    if days_back is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        filtered_posts = []
        for post in posts:
            post_date = datetime.utcfromtimestamp(post.created_utc)
            if post_date >= cutoff_date:
                filtered_posts.append(post)
        posts = filtered_posts
    return list(posts)

def search_reddit_posts(
    query, 
    num_posts=10, 
    sort_by='relevance'
    ) -> list[praw.models.Submission]:
    """
    Search Reddit posts across all subreddits using a query string.
    
    Input:
        query (str): Search query string.
        num_posts (int, optional): Number of posts to return. Default is 10.
        sort_by (str, optional): Sorting method. One of 'relevance', 'hot', 'top', 'new', 'comments'. Default is 'relevance'.
    Output:
        list of praw.models.Submission: List of Reddit post objects matching the search.
    """
    results = reddit.subreddit('all').search(query, sort=sort_by, limit=num_posts)
    return list(results)

def search_subreddit_posts(
    subreddit_name, 
    query, 
    num_posts=10, 
    days_back=99999, 
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
    subreddit = reddit.subreddit(subreddit_name)
    results = subreddit.search(query, sort=sort_by, limit=num_posts, time_filter='all')
    cutoff_date = None
    if days_back is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    for result in results:
        result_date = datetime.utcfromtimestamp(result.created_utc)
        if cutoff_date is None or result_date >= cutoff_date:
            if save_query:
                yield result, query
            else:
                yield result, None

    
def get_posts_comments(
    posts, 
    days_back=30
    ) -> list[praw.models.Comment]:
    """
    Fetch raw comment objects for a given post or list of posts, filtered by days_back.
    
    Input:
        posts (praw.models.Submission or list of praw.models.Submission): Single post object or list of post objects.
        days_back (int, optional): Only comments from the last 'days_back' days are returned. Default is 30.
    Output:
        list of praw.models.Comment: List of raw Reddit comment objects (not processed dicts) matching the filter.
    """
    if not isinstance(posts, list):
        posts = [posts]
    comments = []
    for post in posts:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        try:
            post.comments.replace_more(limit=None)
            _comments = post.comments.list()
            for comment in _comments:
                if isinstance(comment, praw.models.MoreComments):
                    print(comment.comments().__dict__)
                    continue
                comment_date = datetime.utcfromtimestamp(comment.created_utc)
                if comment_date < cutoff_date:
                    continue
                comments.append(comment)  # Return raw comment object
        except Exception as e:
            print(f"Error processing comments for post {post.id}: {e}")
    return comments

def get_user(
    reddit, 
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
        user = reddit.redditor(username)
        # Optionally, trigger a fetch to ensure the user exists (raises exception if not)
        _ = user.id
        return user
    except Exception as e:
        print(f"Error fetching user '{username}': {e}")
        return None


def get_user_posts(
    user, 
    num_posts=10, 
    sort_by='new'
    ) -> list[praw.models.Submission]:
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
    return list(posts)
