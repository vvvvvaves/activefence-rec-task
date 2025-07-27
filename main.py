#!/usr/bin/env python3
"""
AFRT (Antisemitic Hate Speech Detection on Reddit) - Main Pipeline

This script orchestrates the complete pipeline for detecting antisemitic hate speech on Reddit:
1. Multi-threaded data gathering from Reddit
2. Data processing and conversation composition
3. Perspective API assessment for toxicity scoring
4. Conversation sorting by maximum scores
5. Gemini LLM assessment for antisemitism detection

Author: AFRT Team
Date: 2025
"""

import os
import sys
import time
import threading
import argparse
from datetime import datetime
from pathlib import Path
import traceback

# Import project modules
from multi_threaded_gather import gather_data
from data_processing import (
    compose_conversations,
    sort_conversations_by_score,
    to_csv
)
from perspective_assessment import worker as perspective_worker
from gemini_assessment import worker as gemini_worker
from utils import get_gsheets_api, get_targeting_data, reset_spreadsheet_config

# Configuration
DEFAULT_NUM_POSTS = 200
DEFAULT_DAYS_BACK = 99999
DEFAULT_BATCH_SIZE = 50
DEFAULT_PERSPECTIVE_CONTEXT_SIZE = 19000
DEFAULT_GEMINI_CONTEXT_SIZE = 1000000

# File paths
DATA_DIR = Path("data")
CONVERSATIONS_PATH = DATA_DIR / "conversations.csv"
PERSPECTIVES_PATH = DATA_DIR / "perspectives.csv"
PERSPECTIVES_MAX_PATH = DATA_DIR / "perspectives_max.csv"
CONVERSATIONS_SORTED_PATH = DATA_DIR / "conversations_sorted_by_score.csv"
POSTS_PATH = DATA_DIR / "posts.csv"
COMMENTS_PATH = DATA_DIR / "comments.csv"

def setup_directories():
    """Create necessary directories for data storage."""
    directories = [
        DATA_DIR,
        DATA_DIR / "subreddits",
        DATA_DIR / "schemas",
        Path("llm") / "logs",
        Path("llm") / "prompts"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def check_environment():
    """Check if all required environment variables and files are present."""
    required_env_vars = [
        'REDDIT_CLIENT_ID',
        'REDDIT_CLIENT_SECRET', 
        'REDDIT_USERNAME',
        'PERSPECTIVE_API_KEY',
        'GEMINI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file")
        return False
    
    required_files = [
        'targeting.json',
        'client_secrets.json',
        'llm/prompts/detection_prompt.md',
        'data/schemas/geminis_llm_schema.json'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print("✓ Environment check passed")
    return True

def stage_1_data_gathering(num_posts=DEFAULT_NUM_POSTS, days_back=DEFAULT_DAYS_BACK, new_sheet=False):
    """
    Stage 1: Multi-threaded data gathering from Reddit subreddits.
    
    Input:
        num_posts (int): Number of posts to gather per subreddit
        days_back (int): How many days back to search for posts
        new_sheet (bool): Whether to create a new spreadsheet and reset configuration
    
    Output:
        Google Sheets populated with posts and comments data
        Local JSON files in data/subreddits/ directory
    """
    print("\n" + "="*60)
    print("STAGE 1: DATA GATHERING")
    print("="*60)
    
    start_time = time.time()
    
    # Reset spreadsheet configuration if new_sheet is True
    if new_sheet:
        print("Creating new spreadsheet configuration...")
        reset_spreadsheet_config()
    
    # Get targeting data
    targeting_data = get_targeting_data()
    subreddits = targeting_data['subreddits']
    
    # Run the multi-threaded gatherer
    try:
        gather_data(num_posts=num_posts, days_back=days_back)
        print("✓ Data gathering completed successfully")
    except Exception as e:
        print(f"❌ Error during data gathering: {e}")
        raise
    
    elapsed_time = time.time() - start_time
    print(f"Data gathering completed in {elapsed_time:.2f} seconds")
    
    return True

def stage_2_data_processing():
    """
    Stage 2: Process gathered data and compose conversations.
    
    Input:
        Google Sheets with posts and comments data
    
    Output:
        conversations.csv file with composed conversation threads
    """
    print("\n" + "="*60)
    print("STAGE 2: DATA PROCESSING")
    print("="*60)
    
    start_time = time.time()
    
    # Get Google Sheets API configuration
    gsheets_api = get_gsheets_api()
    
    print("Converting Google Sheets data to CSV...")
    
    # Convert posts and comments from Google Sheets to CSV
    try:
        posts_df = to_csv(
            POSTS_PATH,
            service=gsheets_api['google_sheets_service'],
            spreadsheet_id=gsheets_api['spreadsheet_id'],
            sheet_id=gsheets_api['posts_sheet_id']
        )
        print(f"✓ Posts CSV created: {len(posts_df)} posts")
        
        comments_df = to_csv(
            COMMENTS_PATH,
            service=gsheets_api['google_sheets_service'],
            spreadsheet_id=gsheets_api['spreadsheet_id'],
            sheet_id=gsheets_api['comments_sheet_id']
        )
        print(f"✓ Comments CSV created: {len(comments_df)} comments")
        
    except Exception as e:
        print(f"❌ Error converting data to CSV: {e}")
        raise
    
    print("Composing conversations from posts and comments...")
    
    # Compose conversations
    try:
        conversations_df = compose_conversations(
            output_path=CONVERSATIONS_PATH,
            posts_path=POSTS_PATH,
            comments_path=COMMENTS_PATH
        )
        print(f"✓ Conversations composed: {len(conversations_df)} conversations")
        
    except Exception as e:
        print(f"❌ Error composing conversations: {e}")
        raise
    
    elapsed_time = time.time() - start_time
    print(f"Data processing completed in {elapsed_time:.2f} seconds")
    
    return True

def stage_3_perspective_assessment(batch_size=DEFAULT_BATCH_SIZE, context_size=DEFAULT_PERSPECTIVE_CONTEXT_SIZE):
    """
    Stage 3: Assess conversations using Perspective API for toxicity scoring.
    
    Input:
        conversations.csv file with full conversation threads
    
    Output:
        Google Sheets populated with Perspective API scores
        perspectives.csv file with toxicity assessments
    """
    print("\n" + "="*60)
    print("STAGE 3: PERSPECTIVE API ASSESSMENT")
    print("="*60)
    
    start_time = time.time()
    
    if not CONVERSATIONS_PATH.exists():
        print(f"❌ Conversations file not found: {CONVERSATIONS_PATH}")
        raise FileNotFoundError(f"Conversations file not found: {CONVERSATIONS_PATH}")
    
    print(f"Starting Perspective API assessment of conversations...")
    print(f"Batch size: {batch_size}")
    print(f"Context size limit: {context_size} characters")
    
    # Run Perspective API assessment
    try:
        perspective_worker(
            conversations_path=str(CONVERSATIONS_PATH),
            batch_size=batch_size,
            start_row=0,
            context_size=context_size
        )
        print("✓ Perspective API assessment completed successfully")
        
    except Exception as e:
        print(f"❌ Error during Perspective API assessment: {e}")
        raise
    
    # Convert perspectives to CSV
    try:
        gsheets_api = get_gsheets_api()
        perspectives_df = to_csv(
            PERSPECTIVES_PATH,
            service=gsheets_api['google_sheets_service'],
            spreadsheet_id=gsheets_api['spreadsheet_id'],
            sheet_id=gsheets_api['perspectives_sheet_id']
        )
        print(f"✓ Perspectives CSV created: {len(perspectives_df)} assessments")
        
    except Exception as e:
        print(f"❌ Error converting perspectives to CSV: {e}")
        raise
    
    elapsed_time = time.time() - start_time
    print(f"Perspective API assessment completed in {elapsed_time:.2f} seconds")
    
    return True

def stage_4_sort_conversations(required_attributes=None):
    """
    Stage 4: Sort conversations by maximum Perspective API scores.
    
    Input:
        conversations.csv and perspectives.csv files
    
    Output:
        conversations_sorted_by_score.csv file with conversations ranked by toxicity
    """
    print("\n" + "="*60)
    print("STAGE 4: SORTING CONVERSATIONS BY SCORE")
    print("="*60)
    
    start_time = time.time()
    
    if not CONVERSATIONS_PATH.exists():
        print(f"❌ Conversations file not found: {CONVERSATIONS_PATH}")
        raise FileNotFoundError(f"Conversations file not found: {CONVERSATIONS_PATH}")
    
    if not PERSPECTIVES_PATH.exists():
        print(f"❌ Perspectives file not found: {PERSPECTIVES_PATH}")
        raise FileNotFoundError(f"Perspectives file not found: {PERSPECTIVES_PATH}")
    
    print("Sorting conversations by maximum Perspective API scores...")
    
    if required_attributes:
        print(f"Filtering by attributes: {required_attributes}")
    
    # Sort conversations by score
    try:
        sorted_conversations = sort_conversations_by_score(
            conversations_path=str(CONVERSATIONS_PATH),
            perspectives_max_path=str(PERSPECTIVES_PATH),
            output_path=str(CONVERSATIONS_SORTED_PATH),
            required_attributes=required_attributes
        )
        
        if not sorted_conversations.empty:
            print(f"✓ Conversations sorted: {len(sorted_conversations)} conversations")
            print(f"Score range: {sorted_conversations['max_score'].min():.3f} - {sorted_conversations['max_score'].max():.3f}")
        else:
            print("⚠ No conversations found matching the criteria")
            
    except Exception as e:
        print(f"❌ Error sorting conversations: {e}")
        raise
    
    elapsed_time = time.time() - start_time
    print(f"Conversation sorting completed in {elapsed_time:.2f} seconds")
    
    return True

def stage_5_gemini_assessment(batch_size=DEFAULT_BATCH_SIZE, context_size=DEFAULT_GEMINI_CONTEXT_SIZE):
    """
    Stage 5: Assess conversations using Gemini LLM for antisemitism detection.
    
    Input:
        conversations_sorted_by_score.csv file with high-scoring conversations
    
    Output:
        Google Sheets populated with Gemini LLM antisemitism assessments
    """
    print("\n" + "="*60)
    print("STAGE 5: GEMINI LLM ASSESSMENT")
    print("="*60)
    
    start_time = time.time()
    
    # Use sorted conversations if available, otherwise use regular conversations
    input_conversations_path = CONVERSATIONS_SORTED_PATH if CONVERSATIONS_SORTED_PATH.exists() else CONVERSATIONS_PATH
    
    if not input_conversations_path.exists():
        print(f"❌ Conversations file not found: {input_conversations_path}")
        raise FileNotFoundError(f"Conversations file not found: {input_conversations_path}")
    
    print(f"Starting Gemini LLM assessment of conversations...")
    print(f"Input file: {input_conversations_path}")
    print(f"Batch size: {batch_size}")
    print(f"Context size limit: {context_size} characters")
    
    # Run Gemini LLM assessment
    try:
        gemini_worker(
            conversations_path=str(input_conversations_path),
            batch_size=batch_size,
            start_row=0,
            context_size=context_size
        )
        print("✓ Gemini LLM assessment completed successfully")
        
    except Exception as e:
        print(f"❌ Error during Gemini LLM assessment: {e}")
        raise
    
    elapsed_time = time.time() - start_time
    print(f"Gemini LLM assessment completed in {elapsed_time:.2f} seconds")
    
    return True

def run_full_pipeline(args):
    """
    Run the complete AFRT pipeline from data gathering to antisemitism assessment.
    
    Args:
        args: Command line arguments containing pipeline configuration
    """
    print("🚀 AFRT - Antisemitic Hate Speech Detection Pipeline")
    print("="*60)
    
    # Setup and validation
    setup_directories()
    
    if not check_environment():
        print("❌ Environment validation failed. Please fix the issues above.")
        sys.exit(1)
    
    pipeline_start_time = time.time()
    
    try:
        # Stage 1: Data Gathering
        if args.stages == 'all' or 'gather' in args.stages:
            stage_1_data_gathering(
                num_posts=args.num_posts,
                days_back=args.days_back,
                new_sheet=args.new_sheet
            )
        
        # Stage 2: Data Processing
        if args.stages == 'all' or 'process' in args.stages:
            stage_2_data_processing()
        
        # Stage 3: Perspective API Assessment
        if args.stages == 'all' or 'perspective' in args.stages:
            stage_3_perspective_assessment(
                batch_size=args.batch_size,
                context_size=args.perspective_context_size
            )
        
        # Stage 4: Sort Conversations
        if args.stages == 'all' or 'sort' in args.stages:
            stage_4_sort_conversations(
                required_attributes=args.required_attributes
            )
        
        # Stage 5: Gemini LLM Assessment
        if args.stages == 'all' or 'gemini' in args.stages:
            stage_5_gemini_assessment(
                batch_size=args.batch_size,
                context_size=args.gemini_context_size
            )
        
        pipeline_elapsed_time = time.time() - pipeline_start_time
        print("\n" + "="*60)
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Total pipeline execution time: {pipeline_elapsed_time:.2f} seconds")
        print(f"Output files:")
        print(f"  - Posts: {POSTS_PATH}")
        print(f"  - Comments: {COMMENTS_PATH}")
        print(f"  - Conversations: {CONVERSATIONS_PATH}")
        print(f"  - Perspectives: {PERSPECTIVES_PATH}")
        print(f"  - Sorted Conversations: {CONVERSATIONS_SORTED_PATH}")
        print("\nData has also been uploaded to Google Sheets for further analysis.")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)

def main():
    """Main entry point for the AFRT pipeline."""
    parser = argparse.ArgumentParser(
        description="AFRT - Antisemitic Hate Speech Detection Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete pipeline
  python main.py
  
  # Run only data gathering and processing
  python main.py --stages gather,process
  
  # Run with custom parameters
  python main.py --num-posts 100 --batch-size 25 --context-size 15000
  
  # Run only Gemini assessment on sorted conversations
  python main.py --stages gemini
  
  # Filter conversations by specific toxicity attributes
  python main.py --required-attributes toxicity,severe_toxicity,identity_attack
  
  # Create a new spreadsheet and reset configuration
  python main.py --new-sheet
        """
    )
    
    parser.add_argument(
        '--stages',
        type=str,
        default='all',
        help='Pipeline stages to run (comma-separated): gather,process,perspective,sort,gemini,all'
    )
    
    parser.add_argument(
        '--num-posts',
        type=int,
        default=DEFAULT_NUM_POSTS,
        help=f'Number of posts to gather per subreddit (default: {DEFAULT_NUM_POSTS})'
    )
    
    parser.add_argument(
        '--days-back',
        type=int,
        default=DEFAULT_DAYS_BACK,
        help=f'Number of days back to search for posts (default: {DEFAULT_DAYS_BACK})'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f'Batch size for API processing (default: {DEFAULT_BATCH_SIZE})'
    )
    
    parser.add_argument(
        '--perspective-context-size',
        type=int,
        default=DEFAULT_PERSPECTIVE_CONTEXT_SIZE,
        help=f'Maximum context size in characters (default: {DEFAULT_PERSPECTIVE_CONTEXT_SIZE} characters)'
    )

    parser.add_argument(
        '--gemini-context-size',
        type=int,
        default=DEFAULT_GEMINI_CONTEXT_SIZE,
        help=f'Maximum context size in characters (default: {DEFAULT_GEMINI_CONTEXT_SIZE} characters)'
    )
    
    parser.add_argument(
        '--required-attributes',
        type=str,
        help='Comma-separated list of Perspective API attributes to filter by (e.g., toxicity,severe_toxicity)'
    )
    
    parser.add_argument(
        '--new-sheet',
        action='store_true',
        help='Create a new Google Sheets spreadsheet and reset all sheet configurations'
    )
    
    args = parser.parse_args()
    
    # Parse stages argument
    if args.stages == 'all':
        args.stages = ['gather', 'process', 'perspective', 'sort', 'gemini']
    else:
        args.stages = [stage.strip() for stage in args.stages.split(',')]
    
    # Parse required attributes
    if args.required_attributes:
        args.required_attributes = [attr.strip() for attr in args.required_attributes.split(',')]
    
    run_full_pipeline(args)

if __name__ == "__main__":
    main() 