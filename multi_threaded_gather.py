import threading
import time
from tqdm import tqdm
from datetime import datetime
from api import (
    get_client, 
    get_posts_comments, 
    search_subreddit_posts
    )
from llm.perspective_api import (
    get_client as get_perspective_client, 
    get_perspective_api_score, 
    clean_response_flat
    )
from submodules.google_api.google_sheets_api import (
    add_rows_to_sheet
    )
from utils import get_targeting_data, to_dict, save_json, get_gsheets_api
import random
import os
import json

NUM_POSTS = 200
DAYS_BACK = 99999
POSTS_PER_QUERY = 40
REDDIT_RATE_LIMIT_SECONDS = 0.6 # 100 requests per minute
PERSPECTIVE_RATE_LIMIT_SECONDS = 1 # 1 request per second

gsheets_api = get_gsheets_api()

google_sheets_service = gsheets_api['google_sheets_service']
spreadsheet_id = gsheets_api['spreadsheet_id']
POSTS_SHEET_ID = gsheets_api['posts_sheet_id']
COMMENTS_SHEET_ID = gsheets_api['comments_sheet_id']


# Worker function for each subreddit
def worker(subreddit_name, progress_bar=None):
    client = get_client()
    perspective_client = get_perspective_client()
    search_terms = get_targeting_data()['search_terms']
    search_terms_neutral = get_targeting_data()['search_terms_neutral']
    posts_collected = 0

    def get_posts(query, num_posts_per_query):
        return search_subreddit_posts(
            client,
            subreddit_name=subreddit_name,
            query=query,
            num_posts=num_posts_per_query,
            days_back=DAYS_BACK,
            sort_by='new',
            save_query=True
        )

    def get_comments(post):
        return get_posts_comments(client, post)

    def clean_post(post, query):
        post_dict = to_dict(post)[0]
        post_dict['query'] = query
        return post_dict

    def clean_comments(comments, query):
        comments_dict = to_dict(comments)
        for comment in comments_dict:
            comment['query'] = query
        return comments_dict

    def score_with_perspective(text):
        return clean_response_flat(get_perspective_api_score(perspective_client, text))

    def add_perspective_to_post(post_dict):
        text = post_dict['title'] + ' ' + post_dict['selftext']
        perspective_scores = score_with_perspective(text)
        if perspective_scores is not None:
            post_dict.update(perspective_scores)
        return post_dict

    def add_perspective_to_comments(comments_dict):
        for comment in comments_dict:
            comment_text = comment['body']
            comment_perspective_scores = score_with_perspective(comment_text)
            if comment_perspective_scores is not None:
                comment.update(comment_perspective_scores)
        return comments_dict

    def save_post_and_comments(post_dict, comments_dict, post_id, post_created):
        save_json(post_dict, f"data/subreddits/{subreddit_name}/posts/post_{post_id}_{int(post_created)}.json")
        save_json(comments_dict, f"data/subreddits/{subreddit_name}/comments/comments_{post_id}.json")
        
    def save_comments_to_gsheets(comments_dict):
        add_rows_to_sheet(google_sheets_service, spreadsheet_id, COMMENTS_SHEET_ID, comments_dict, list(comments_dict[0].keys()))
    
    def save_posts_to_gsheets(posts_dict):
        add_rows_to_sheet(google_sheets_service, spreadsheet_id, POSTS_SHEET_ID, posts_dict, list(posts_dict[0].keys()))

    # Every API call requests N posts. 
    # Some search terms return less than N posts because they are ineffective at targeting.
    # In such cases, we do not want to waste time requesting more posts.
    # Therefore, the count goes for number of posts REQUESTED, not number of posts COLLECTED.
    posts_requested = 0
    while posts_requested < NUM_POSTS:
        num_posts_per_query = min(POSTS_PER_QUERY, NUM_POSTS - posts_requested)
        random_neg = random.choice(search_terms)
        random_neut = random.choice(search_terms_neutral)
        query = f"{random_neg} {random_neut}"
        generator = get_posts(query, num_posts_per_query)
        time.sleep(REDDIT_RATE_LIMIT_SECONDS) # Sleep after every posts request
        posts_dict = []
        all_comments_dict = []
        for post, _ in generator:
            posts_requested += num_posts_per_query
            comments = get_comments(post)
            time.sleep(REDDIT_RATE_LIMIT_SECONDS) # Sleep after every comments request
            post_dict = clean_post(post, query)
            post_created = post_dict['created']
            post_id = post_dict['id']
            comments_dict = clean_comments(comments, query)
            if comments_dict:
                all_comments_dict.extend(comments_dict)
            posts_dict.append(post_dict)
            if progress_bar:
                progress_bar.update(num_posts_per_query)
            if posts_requested >= NUM_POSTS:
                break
        if posts_dict:
            save_posts_to_gsheets(posts_dict)
        if all_comments_dict:
            save_comments_to_gsheets(all_comments_dict)
    if progress_bar:
        progress_bar.close()

def main():
    subreddits = get_targeting_data()['subreddits']
    # Only start as many workers as there are subreddits
    threads = []
    progress_bars = []
    for i, subreddit in enumerate(subreddits):
        os.makedirs(f"data/subreddits/{subreddit}/posts", exist_ok=True)
        os.makedirs(f"data/subreddits/{subreddit}/comments", exist_ok=True)
        pbar = tqdm(total=NUM_POSTS, desc=f"{subreddit}", position=i+1, leave=True)
        progress_bars.append(pbar)
        t = threading.Thread(target=worker, args=(subreddit, pbar), daemon=True)
        threads.append(t)
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted! Exiting...")
        for pbar in progress_bars:
            pbar.close()

if __name__ == "__main__":
    main() 