#!/usr/bin/env python3
"""
Perspective API Assessment Module for AFRT Pipeline

This module implements Stage 3 of the AFRT pipeline: toxicity assessment using
Google's Perspective API. It processes conversation threads and scores them for
various toxicity attributes including TOXICITY, SEVERE_TOXICITY, IDENTITY_ATTACK,
INSULT, PROFANITY, THREAT, ATTACK_ON_AUTHOR, ATTACK_ON_COMMENTER, and INFLAMMATORY.

The module includes comprehensive error handling, rate limiting, and logging
to ensure reliable processing of large datasets.

Author: AFRT Team
Date: 2025
"""

from llm.perspective_api import get_client, get_perspective_api_score, clean_response_flat
from llm.perspective_logger import setup_perspective_logger, log_perspective_error
import json
from utils import get_gsheets_api
from submodules.google_api.google_sheets_api import get_rows_from_range, add_rows_to_sheet
import uuid
import time
from tqdm import tqdm
import pandas as pd
import argparse
from googleapiclient.errors import HttpError

# Configuration Constants
CONTEXT_SIZE_LIMIT = 19000  # Character limit to stay well under 20480 byte API limit
BATCH_SIZE = 50  # Number of conversations to process in each batch
START_ROW = 0  # Starting row for processing (useful for resuming interrupted runs)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conversations_path', type=str, default='data/conversations.csv')
    parser.add_argument('-b', '--batch_size', type=int, default=BATCH_SIZE)
    parser.add_argument('-s', '--start_row', type=int, default=START_ROW)
    parser.add_argument('-cs', '--context_size', type=int, default=CONTEXT_SIZE_LIMIT   )
    return parser.parse_args()

def worker(conversations_path, batch_size=BATCH_SIZE, start_row=START_ROW, context_size=CONTEXT_SIZE_LIMIT):
    """
    Process conversations for Perspective API toxicity assessment.
    
    This function processes conversation threads in batches and sends them to
    Google's Perspective API for toxicity scoring. It handles rate limiting,
    error recovery, and comprehensive logging of the assessment process.
    
    Args:
        conversations_path (str): Path to the conversations CSV file
        batch_size (int): Number of conversations to process in each batch
        start_row (int): Starting row for processing (useful for resuming)
        context_size (int): Maximum character limit for API requests
    
    Input:
        - conversations.csv file with full conversation threads
        - Perspective API credentials
        - Google Sheets API configuration
    
    Output:
        - Google Sheets populated with Perspective API scores
        - Error logs for failed assessments
        - Progress tracking for monitoring
    """
    # Initialize APIs and services
    gsheets_api = get_gsheets_api()
    spreadsheet_id = gsheets_api['spreadsheet_id']
    perspectives_sheet_id = gsheets_api['perspectives_sheet_id']
    google_sheets_service = gsheets_api['google_sheets_service']
    perspective_client = get_client()
    
    # Setup logger for Perspective API errors
    logger = setup_perspective_logger()
    
    # Get column headers from the sheet
    perspective_columns = get_rows_from_range(google_sheets_service, spreadsheet_id, perspectives_sheet_id, 1, 1)[0]
    
    # Load conversations data
    conversations_df = pd.read_csv(conversations_path)
    
    # Setup progress bars
    assessment_bar = tqdm(total=None, dynamic_ncols=True, bar_format='Conversations assessed: {n}')
    uploaded_bar = tqdm(total=None, dynamic_ncols=True, bar_format='Conversations uploaded: {n}')
    assessment_bar.update(start_row)
    uploaded_bar.update(start_row)
    assessment_bar.refresh()
    uploaded_bar.refresh()
    
    batch_index = 0
    
    while True:
        # Get batch of conversations
        batch_df = conversations_df.iloc[batch_index * batch_size + start_row: (batch_index + 1) * batch_size + start_row]
        if len(batch_df) < 1:
            break
            
        perspective_rows = []
        
        for index, row in batch_df.iterrows():
            # Get the full conversation text
            conversation_text = row['full_conversation']
            post_id = row['post_id']
            # subreddit = row['subreddit']
            if conversation_text is None or pd.isna(conversation_text):
                continue
                
            # Truncate text if needed (use first n characters for conversations)
            # Ensure we stay under 20480 bytes limit for Perspective API
            max_chars = min(context_size, CONTEXT_SIZE_LIMIT)
            if len(conversation_text) > max_chars:
                conversation_text = conversation_text[:max_chars]
            
            try:
                # Get perspective API score
                response = get_perspective_api_score(perspective_client, conversation_text)
            except HttpError as e:
                # Log the error with detailed information
                error_message = f"HTTP Error {e.status_code}"
                error_details = f"Status: {e.status_code}, Reason: {e.reason}"
                log_perspective_error(
                    logger, 
                    post_id, 
                    len(conversation_text), 
                    error_message, 
                    error_details
                )
                
                if e.status_code == 429:
                    # Rate limit error - wait and retry
                    time.sleep(10)
                    try:
                        response = get_perspective_api_score(perspective_client, conversation_text)
                    except HttpError as retry_e:
                        # Log retry error
                        retry_error_message = f"HTTP Error on retry {retry_e.status_code}"
                        retry_error_details = f"Status: {retry_e.status_code}, Reason: {retry_e.reason}"
                        log_perspective_error(
                            logger, 
                            post_id, 
                            len(conversation_text), 
                            retry_error_message, 
                            retry_error_details
                        )
                        continue  # Skip this conversation and continue with next
                else:
                    # Non-rate limit error - skip this conversation
                    continue
            except Exception as e:
                # Log any other unexpected errors
                error_message = f"Unexpected error: {type(e).__name__}"
                error_details = str(e)
                log_perspective_error(
                    logger, 
                    post_id, 
                    len(conversation_text), 
                    error_message, 
                    error_details
                )
                continue  # Skip this conversation and continue with next
            
            assessment_bar.update(1)
            assessment_bar.refresh()
            
            # Clean and format response
            clean_response = clean_response_flat(response)
            if clean_response is None:
                # Log when response is None (usually bad request or unknown language)
                log_perspective_error(
                    logger, 
                    post_id, 
                    len(conversation_text), 
                    "Response is None", 
                    "Bad request or unknown language detected"
                )
                continue
                
            # Add conversation-specific fields
            clean_response['perspective_id'] = str(uuid.uuid4())
            clean_response['sheet_name'] = 'conversations'
            clean_response['post_id'] = post_id
            # clean_response['subreddit'] = subreddit
            
            perspective_rows.append(clean_response)
            
            # Rate limiting
            time.sleep(1.1)
        
        # Upload batch to Google Sheets
        if perspective_rows:
            add_rows_to_sheet(
                google_sheets_service, spreadsheet_id, perspectives_sheet_id,
                perspective_rows,
                [column.lower() for column in perspective_columns]
            )
            uploaded_bar.update(len(perspective_rows))
            uploaded_bar.refresh()
        
        batch_index += 1
    
    assessment_bar.close()
    uploaded_bar.close()

if __name__ == '__main__':
    args = get_args()
    worker(
        conversations_path=args.conversations_path,
        batch_size=args.batch_size,
        start_row=args.start_row,
        context_size=args.context_size
    )