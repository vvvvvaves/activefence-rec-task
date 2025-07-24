import concurrent.futures
import os
from health_metrics import assess_community_health
from api import get_client
from utils import get_targeting_data
from itertools import repeat

subreddits = get_targeting_data()['subreddits']
print(subreddits)

for subreddit in subreddits:
    if os.path.exists(f"data/{subreddit}"):
        subreddits.remove(subreddit)

max_workers = min(32, (os.cpu_count() or 1) * 2)

print(f"Assessing {len(subreddits)} subreddits with {max_workers} threads")

reddit = get_client()

with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    executor.map(lambda x: assess_community_health(get_client(), x, num_posts=5, days_back=30), subreddits)
