#!/usr/bin/env python3
"""
Multi-threaded Reddit Data Gatherer for AFRT Pipeline

This module implements Stage 1 of the AFRT pipeline: multi-threaded data gathering
from Reddit subreddits using targeted search terms for antisemitic hate speech detection.

The gatherer creates one thread per subreddit and collects posts and comments using
a combination of antisemitic and neutral search terms to ensure comprehensive coverage
while maintaining plausible deniability in the search process.

Author: AFRT Team
Date: 2025
"""

import threading
import time
import signal
import sys
from tqdm import tqdm
from datetime import datetime
import prawcore
from reddit_api import (
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
from logs.gather_logger import setup_gather_logger, log_gather_error, log_gather_info, log_gather_warning, stop_gather_logger
import random
import os
import json
import queue

# Configuration Constants
NUM_POSTS = 200  # Number of posts to collect per subreddit
DAYS_BACK = 99999  # How many days back to search for posts
POSTS_PER_QUERY = 40  # Number of posts to request per search query
REDDIT_RATE_LIMIT_SECONDS = 0.6  # Rate limit: 100 requests per minute
PERSPECTIVE_RATE_LIMIT_SECONDS = 1  # Rate limit: 1 request per second
REDDIT_TOO_MANY_REQUESTS_SLEEP_SECONDS = 60
NUM_WORKERS = 0

# Google Sheets API configuration
google_sheets_service = None
spreadsheet_id = None
POSTS_SHEET_ID = None
COMMENTS_SHEET_ID = None

# Global variables for graceful shutdown
shutdown_event = threading.Event()
active_threads = []

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nReceived interrupt signal. Shutting down gracefully...")
    shutdown_event.set()
    # Give threads a chance to finish
    time.sleep(2)
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

# Thread-safe progress bar manager
class ProgressBarManager:
    def __init__(self, total_subreddits, total_posts_per_subreddit):
        self.lock = threading.Lock()
        self.progress_bars = {}
        self.total_posts = total_posts_per_subreddit
        
        # Create a single tqdm instance for all subreddits
        self.overall_pbar = tqdm(
            total=total_subreddits * total_posts_per_subreddit,
            desc="Overall Progress",
            position=0,
            leave=True,
            ncols=100
        )
        
    def update_progress(self, subreddit_name, posts_collected):
        """Thread-safe progress update"""
        with self.lock:
            if subreddit_name not in self.progress_bars:
                self.progress_bars[subreddit_name] = 0
            old_count = self.progress_bars[subreddit_name]
            self.progress_bars[subreddit_name] = posts_collected
            increment = posts_collected - old_count
            if increment > 0:
                self.overall_pbar.update(increment)
                
    def close(self):
        """Close the progress bar"""
        with self.lock:
            self.overall_pbar.close()


def worker(subreddit_name, num_posts=NUM_POSTS, days_back=DAYS_BACK, progress_manager=None, logger=None):
    global active_threads
    active_threads.append(threading.current_thread())
    """
    Worker function for each subreddit thread.
    
    This function runs in a separate thread for each subreddit and handles:
    - Searching for posts using antisemitic and neutral search terms
    - Collecting comments for each post
    - Applying Perspective API scoring to posts and comments
    - Saving data to Google Sheets and local JSON files
    
    Args:
        subreddit_name (str): Name of the subreddit to process
        progress_bar (tqdm, optional): Progress bar for monitoring
        logger: Shared logger instance for thread-safe logging
    
    Input:
        - Reddit API client
        - Perspective API client
        - Search terms from targeting.json
        - Google Sheets API configuration
    
    Output:
        - Google Sheets populated with posts and comments
        - Local JSON files in data/subreddits/{subreddit}/ directory
    """
    # Use the shared logger instance passed from main thread
    if logger is None:
        logger = setup_gather_logger()
    
    client = get_client()
    perspective_client = get_perspective_client()
    search_terms = get_targeting_data()['search_terms']

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

    # Main data collection loop
    # Track posts REQUESTED rather than posts COLLECTED because some search terms
    # may return fewer posts than requested due to being ineffective at targeting.
    # This ensures we don't waste time on ineffective search terms.
    posts_requested = 0
    log_gather_info(logger, subreddit_name, f"Starting data collection for {num_posts} posts")
    while posts_requested < num_posts and not shutdown_event.is_set():
        num_posts_per_query = min(POSTS_PER_QUERY, num_posts - posts_requested)
        log_gather_info(logger, subreddit_name, f"Collecting {num_posts_per_query} posts")
        if num_posts_per_query == 0:
            log_gather_info(logger, subreddit_name, f"Reached target of {num_posts} posts")
            break
        query = random.choice(search_terms)
        try:
            if shutdown_event.is_set():
                log_gather_info(logger, subreddit_name, "Shutdown requested, stopping collection")
                break
                
            log_gather_info(logger, subreddit_name, f"Requesting {num_posts_per_query} posts with query: '{query}'")
            generator = get_posts(query, num_posts_per_query)
            time.sleep(REDDIT_RATE_LIMIT_SECONDS*NUM_WORKERS) # Sleep after every posts request
            posts_requested += num_posts_per_query  # Increment by the number of posts we requested
            posts_dict = []
            all_comments_dict = []
            
            for post, _ in generator:
                if shutdown_event.is_set():
                    break
                try:
                    log_gather_info(logger, subreddit_name, f"Getting comments for post {post.id}")
                    comments = get_comments(post)
                    time.sleep(REDDIT_RATE_LIMIT_SECONDS*NUM_WORKERS) # Sleep after every comments request
                    post_dict = clean_post(post, query)
                    post_created = post_dict['created']
                    post_id = post_dict['id']
                    comments_dict = clean_comments(comments, query)
                    if comments_dict:
                        all_comments_dict.extend(comments_dict)
                    posts_dict.append(post_dict)
                    log_gather_info(logger, subreddit_name, f"Collected post {post_id} with {len(comments_dict)} comments")
                except prawcore.exceptions.TooManyRequests as e:
                    log_gather_error(logger, subreddit_name, f"Rate limit hit while getting comments for post {post.id}: {e}")
                    log_gather_info(logger, subreddit_name, f"Sleeping for {REDDIT_TOO_MANY_REQUESTS_SLEEP_SECONDS} seconds")
                    time.sleep(REDDIT_TOO_MANY_REQUESTS_SLEEP_SECONDS)
                    continue
                except Exception as e:
                    log_gather_error(logger, subreddit_name, f"Error processing post {post.id}: {e}")
                    continue
                    
            if progress_manager:
                progress_manager.update_progress(subreddit_name, num_posts_per_query)  # Update progress with actual posts requested
                
            log_gather_info(logger, subreddit_name, f"Query '{query}' completed: Requested {posts_requested} posts")
            
            if posts_dict:
                save_posts_to_gsheets(posts_dict)
                log_gather_info(logger, subreddit_name, f"Saved {len(posts_dict)} posts to Google Sheets")
            if all_comments_dict:
                save_comments_to_gsheets(all_comments_dict)
                log_gather_info(logger, subreddit_name, f"Saved {len(all_comments_dict)} comments to Google Sheets")
                
        except prawcore.exceptions.TooManyRequests:
            log_gather_error(logger, subreddit_name, f"prawcore.exceptions.TooManyRequests: Too many requests for subreddit {subreddit_name}")
            log_gather_info(logger, subreddit_name, f"Sleeping for {REDDIT_TOO_MANY_REQUESTS_SLEEP_SECONDS} seconds")
            time.sleep(REDDIT_TOO_MANY_REQUESTS_SLEEP_SECONDS)
            continue
        except Exception as e:
            log_gather_error(logger, subreddit_name, f"Error in main collection loop: {e}")
            log_gather_error(logger, subreddit_name, f"Exception type: {type(e).__name__}")
            break
    
    log_gather_info(logger, subreddit_name, f"Worker thread completed. Requested {posts_requested} posts")
    # Progress bar is managed by the main thread, no need to close here

def gather_data(num_posts=NUM_POSTS, days_back=DAYS_BACK):
    """
    Main function to orchestrate multi-threaded data gathering.
    
    Creates one thread per subreddit and manages the overall data collection process.
    Each thread runs independently and collects data from its assigned subreddit.
    
    Input:
        - targeting.json configuration with subreddits and search terms
        - Reddit API credentials
        - Google Sheets API configuration
    
    Output:
        - Google Sheets populated with posts and comments data
        - Local JSON files organized by subreddit
        - Progress bars showing collection status for each subreddit
    """
    # Setup logger for main process - this will be shared across all threads
    logger = setup_gather_logger()
    
    global google_sheets_service, spreadsheet_id, POSTS_SHEET_ID, COMMENTS_SHEET_ID
    gsheets_api = get_gsheets_api()
    google_sheets_service = gsheets_api['google_sheets_service']
    spreadsheet_id = gsheets_api['spreadsheet_id']
    POSTS_SHEET_ID = gsheets_api['posts_sheet_id']
    COMMENTS_SHEET_ID = gsheets_api['comments_sheet_id']
    subreddits = get_targeting_data()['subreddits']
    
    print(f"Starting data gathering from {len(subreddits)} subreddits...")
    print(f"Target: {num_posts} posts per subreddit")
    print(f"Search period: Last {days_back} days")
    
    log_gather_info(logger, "MAIN", f"Starting data gathering from {len(subreddits)} subreddits")
    log_gather_info(logger, "MAIN", f"Target: {num_posts} posts per subreddit, Search period: Last {days_back} days")
    
    # Create threads and progress bar manager
    threads = []
    global NUM_WORKERS
    NUM_WORKERS = len(subreddits)
    
    # Create a single progress bar manager for all threads
    progress_manager = ProgressBarManager(len(subreddits), num_posts)
    
    for subreddit in subreddits:
        # Create and start worker thread
        t = threading.Thread(target=worker, args=(subreddit, num_posts, days_back, progress_manager, logger), daemon=True)
        threads.append(t)
        t.start()
    
    # Monitor threads until completion
    try:
        log_gather_info(logger, "MAIN", f"Created {len(threads)} worker threads, monitoring for completion")
        monitoring_start_time = time.time()
        last_log_time = monitoring_start_time
        
        while any(t.is_alive() for t in threads) and not shutdown_event.is_set():
            current_time = time.time()
            time.sleep(1)
            
            # Log status every 30 seconds
            if current_time - last_log_time >= 30:
                alive_threads = sum(1 for t in threads if t.is_alive())
                elapsed_time = current_time - monitoring_start_time
                log_gather_info(logger, "MAIN", f"Monitoring: {alive_threads}/{len(threads)} threads still alive after {elapsed_time:.1f} seconds")
                last_log_time = current_time
        
        if shutdown_event.is_set():
            log_gather_warning(logger, "MAIN", "Shutdown requested, waiting for threads to finish")
            # Wait a bit more for threads to finish gracefully
            time.sleep(5)
            
        log_gather_info(logger, "MAIN", "All worker threads completed")
        progress_manager.close()
        
    except Exception as e:
        log_gather_error(logger, "MAIN", f"Error in main monitoring loop: {e}")
        progress_manager.close()
        raise
    finally:
        # Always stop the logger properly
        stop_gather_logger()

if __name__ == "__main__":
    gather_data() 