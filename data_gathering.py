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

NUM_POSTS = 200
DAYS_BACK = 99999

def continuously_gather_data(_func, subreddit_name, progress_bar, *args, **kwargs):
    posts = _func(subreddit_name=subreddit_name, *args, **kwargs)
    for post in posts:
        comments = get_posts_comments(post)
        posts_dict = to_dict([post])
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
            executor.submit(continuously_gather_data, get_subreddit_posts, x, progress_bars[i], num_posts=NUM_POSTS, days_back=DAYS_BACK)
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
