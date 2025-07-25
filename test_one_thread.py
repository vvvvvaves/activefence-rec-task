from data_gathering import rotate_search_subreddit_posts, continuously_gather_data
from api import get_client
from tqdm import tqdm

reddit = get_client()

NUM_POSTS = 200
DAYS_BACK = 99999

continuously_gather_data(
        rotate_search_subreddit_posts, 
        'Israel', 
        tqdm(total=NUM_POSTS, desc="Israel", position=0, leave=True), 
        num_posts=NUM_POSTS, 
        days_back=DAYS_BACK, 
        sort_by='new', 
        save_query=True
        )