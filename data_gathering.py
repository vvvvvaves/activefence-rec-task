import concurrent.futures
import os
from api import (
    get_client, 
    get_posts_comments, 
    get_subreddit_posts, 
    search_reddit_posts, 
    search_subreddit_posts,
    get_user_posts)
from utils import get_targeting_data, to_dict, save_json
from tqdm import tqdm
import random
import praw
from typing import Generator

NUM_POSTS = 200
DAYS_BACK = 99999

def rotate_search_subreddit_posts(
    subreddit_name, 
    num_posts=10, days_back=99999, 
    sort_by='new', save_query=False
) -> Generator[tuple[praw.models.Submission, str], None, None]: 

    search_terms = get_targeting_data()['search_terms']
    search_terms_neutral = get_targeting_data()['search_terms_neutral']

    neg_rand_index = random.randint(0, len(search_terms) - 1)
    neut_rand_index = random.randint(0, len(search_terms_neutral) - 1)

    query = f"{search_terms[neg_rand_index]} {search_terms_neutral[neut_rand_index]}"

    for i in range(num_posts):
        random_neg = random.choice(search_terms)
        random_neut = random.choice(search_terms_neutral)
        query = f"{random_neg} {random_neut}"
        generator = search_subreddit_posts(
            subreddit_name=subreddit_name, 
            query=query, 
            num_posts=1, 
            days_back=days_back, 
            sort_by=sort_by, 
            save_query=save_query
            )
        for post, _ in generator:
            yield post, query

def continuously_gather_data(_func, subreddit_name, progress_bar, *args, **kwargs):
    generator = _func(subreddit_name=subreddit_name, *args, **kwargs)
    for post, query in generator:
        comments = get_posts_comments(post)
        posts_dict = to_dict(post)
        if kwargs.get('save_query', False):
            for i in range(len(posts_dict)):
                posts_dict[i]['query'] = query
        post_timestamp = post.created
        post_id = post.id
        comments_dict = to_dict(comments)
        save_json(posts_dict, f"data/subreddits/{subreddit_name}/posts/post_{post_id}_{post_timestamp}.json")
        save_json(comments_dict, f"data/subreddits/{subreddit_name}/comments/comments_{post_id}.json")
        progress_bar.update(1)
    progress_bar.close()

def main():
    subreddits = get_targeting_data()['subreddits']

    for subreddit in subreddits:
        if os.path.exists(f"data/{subreddit}"):
            subreddits.remove(subreddit)

    max_workers = min(32, (os.cpu_count() or 1) * 2)

    print(f"Assessing {len(subreddits)} subreddits with {max_workers} threads")

    reddit = get_client()

    progress_bars = [
        tqdm(total=NUM_POSTS, desc=f"{subreddit}", position=i, leave=True)
        for i, subreddit in enumerate(subreddits)
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                continuously_gather_data, 
                rotate_search_subreddit_posts, 
                x, 
                progress_bars[i], 
                num_posts=NUM_POSTS, 
                days_back=DAYS_BACK, 
                sort_by='new', 
                save_query=True
                )
            for i, x in enumerate(subreddits)
        ]
        try:
            for future in concurrent.futures.as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            print("Interrupted! Cancelling threads...")
            for future in futures:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            raise

if __name__ == "__main__":
    main()
