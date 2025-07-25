import threading
import time
from tqdm import tqdm
from datetime import datetime
from api import get_client, get_posts_comments, search_subreddit_posts
from utils import get_targeting_data, to_dict, save_json
import random
import os

# Shared rate limit info
latest_rate_limit = {'info': None}
rate_limit_lock = threading.Lock()

NUM_POSTS = 200
DAYS_BACK = 99999

# Worker function for each subreddit
def worker(subreddit_name, progress_bar):
    client = get_client()
    search_terms = get_targeting_data()['search_terms']
    search_terms_neutral = get_targeting_data()['search_terms_neutral']
    posts_collected = 0
    while posts_collected < NUM_POSTS:
        num_posts_per_query = min(20, NUM_POSTS - posts_collected)
        random_neg = random.choice(search_terms)
        random_neut = random.choice(search_terms_neutral)
        query = f"{random_neg} {random_neut}"
        generator = search_subreddit_posts(
            client,
            subreddit_name=subreddit_name,
            query=query,
            num_posts=num_posts_per_query,
            days_back=DAYS_BACK,
            sort_by='new',
            save_query=True
        )
        for post, _ in generator:
            comments = get_posts_comments(client, post)
            posts_dict = to_dict(post)
            for i in range(len(posts_dict)):
                posts_dict[i]['query'] = query
            post_timestamp = post.created
            post_id = post.id
            comments_dict = to_dict(comments)
            save_json(posts_dict, f"data/subreddits/{subreddit_name}/posts/post_{post_id}_{int(post_timestamp)}.json")
            save_json(comments_dict, f"data/subreddits/{subreddit_name}/comments/comments_{post_id}.json")
            progress_bar.update(1)
            posts_collected += 1
            # Update the shared rate limit info
            limits = client.auth.limits
            with rate_limit_lock:
                latest_rate_limit['info'] = limits
            if limits['remaining'] < (limits['remaining']+limits['used'])//2:
                time.sleep(60) # sleep if we've hit 50% of the rate limit
            if posts_collected >= NUM_POSTS:
                break
    progress_bar.close()

# Printer thread for rate limit status
def printer():
    last_printed = None
    pbar = None
    while True:
        with rate_limit_lock:
            current = latest_rate_limit['info']
        if current != last_printed and current is not None:
            used = current.get('used') or 0
            remaining = current.get('remaining') or 0
            total = used + remaining
            reset_ts = current.get('reset_timestamp')
            reset_str = datetime.fromtimestamp(reset_ts).strftime('%Y-%m-%d %H:%M:%S') if reset_ts else 'N/A'
            desc = f"Rate limit (resets: {reset_str})"
            if pbar is None:
                pbar = tqdm(total=total, desc=desc, position=0, leave=True)
            else:
                pbar.total = total
                pbar.set_description(desc)
            pbar.n = used
            pbar.refresh()
            last_printed = current
        time.sleep(0.1)

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
    # Start the single printer thread
    printer_thread = threading.Thread(target=printer, daemon=True)
    printer_thread.start()
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted! Exiting...")
        for pbar in progress_bars:
            pbar.close()
        # Threads are daemonic, so will exit

if __name__ == "__main__":
    main() 