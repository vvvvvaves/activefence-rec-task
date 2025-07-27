#!/usr/bin/env python3
"""
Gemini LLM Assessment Module for AFRT Pipeline

This module implements Stage 5 of the AFRT pipeline: advanced antisemitism detection
using Google's Gemini 2.5 Flash LLM. It processes conversation threads that have been
pre-screened by the Perspective API and provides detailed antisemitism assessments
with reasoning and confidence levels.

The module uses a sophisticated prompt engineering approach to detect both explicit
and implicit antisemitic content, including dog whistles, coded language, and
conspiracy theories.

Author: AFRT Team
Date: 2025
"""

from llm.gemini_api import get_client, gemini_generate_structured
from llm.gemini_logger import setup_gemini_logger, log_gemini_error
import json
from utils import get_gsheets_api
from submodules.google_api.google_sheets_api import get_rows_from_range, add_rows_to_sheet
import uuid
import time
from tqdm import tqdm
import pandas as pd
import argparse
from googleapiclient.errors import HttpError
import os
from json.decoder import JSONDecodeError

# Configuration Constants
CONTEXT_SIZE_LIMIT = 19000  # Character limit to stay well under token limits
BATCH_SIZE = 50  # Number of conversations to process in each batch
START_ROW = 0  # Starting row for processing (useful for resuming interrupted runs)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conversations_path', type=str, default='data/conversations.csv')
    parser.add_argument('-b', '--batch_size', type=int, default=BATCH_SIZE)
    parser.add_argument('-s', '--start_row', type=int, default=START_ROW)
    parser.add_argument('-cs', '--context_size', type=int, default=CONTEXT_SIZE_LIMIT)
    return parser.parse_args()

def load_detection_prompt():
    """
    Load the antisemitism detection prompt from the prompts directory.
    
    Returns:
        str: The complete detection prompt for Gemini LLM
    
    Input:
        - llm/prompts/detection_prompt.md file
    
    Output:
        - Formatted prompt string for LLM processing
    """
    prompt_path = os.path.join('llm', 'prompts', 'detection_prompt.md')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def load_gemini_schema():
    """
    Load the structured output schema for Gemini LLM responses.
    
    Returns:
        dict: JSON schema defining the expected output format
    
    Input:
        - data/schemas/geminis_llm_schema.json file
    
    Output:
        - Schema dictionary for structured LLM responses
    """
    schema_path = os.path.join('data', 'schemas', 'geminis_llm_schema.json')
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def worker(conversations_path, batch_size=BATCH_SIZE, start_row=START_ROW, context_size=CONTEXT_SIZE_LIMIT):
    """
    Process conversations for Gemini LLM antisemitism assessment.
    
    This function processes conversation threads using Google's Gemini 2.5 Flash LLM
    to detect antisemitic content. It uses a sophisticated prompt engineering approach
    to identify both explicit and implicit antisemitism, including dog whistles,
    coded language, and conspiracy theories.
    
    Args:
        conversations_path (str): Path to the conversations CSV file
        batch_size (int): Number of conversations to process in each batch
        start_row (int): Starting row for processing (useful for resuming)
        context_size (int): Maximum character limit for API requests
    
    Input:
        - conversations.csv file with conversation threads
        - Gemini API credentials
        - Detection prompt and schema files
        - Google Sheets API configuration
    
    Output:
        - Google Sheets populated with Gemini assessments
        - Structured antisemitism detection results
        - Error logs for failed assessments
        - Token usage and request statistics
    """
    # Initialize APIs and services
    gsheets_api = get_gsheets_api()
    spreadsheet_id = gsheets_api['spreadsheet_id']
    geminis_sheet_id = gsheets_api['geminis_sheet_id']
    google_sheets_service = gsheets_api['google_sheets_service']
    gemini_client = get_client()
    
    # Setup logger for Gemini API errors
    logger = setup_gemini_logger()
    
    # Load prompt and schema
    system_instruction = load_detection_prompt()
    response_schema = load_gemini_schema()
    
    # Get column headers from the sheet
    gemini_columns = get_rows_from_range(google_sheets_service, spreadsheet_id, geminis_sheet_id, 1, 1)[0]
    
    # Load conversations data
    conversations_df = pd.read_csv(conversations_path)
    total_conversations = len(conversations_df)
    
    # Initialize counters
    conversations_analyzed = start_row
    total_tokens_used = 0
    total_requests_sent = 0
    
    # Setup single progress bar with multiple metrics
    progress_bar = tqdm(
        total=total_conversations,
        initial=start_row,
        dynamic_ncols=True,
        bar_format='Conversations: {n_fmt}/{total_fmt} | Tokens: {postfix[0]} | Requests: {postfix[1]}',
        postfix={'tokens': 0, 'requests': 0}
    )
    
    batch_index = 0
    
    while True:
        # Get batch of conversations
        batch_df = conversations_df.iloc[batch_index * batch_size + start_row: (batch_index + 1) * batch_size + start_row]
        if len(batch_df) < 1:
            break
            
        gemini_rows = []
        
        for index, row in batch_df.iterrows():
            # Get the full conversation text
            conversation_text = row['full_conversation']
            post_id = row['post_id']
            
            if conversation_text is None or pd.isna(conversation_text):
                continue
                
            # Truncate text if needed
            max_chars = min(context_size, CONTEXT_SIZE_LIMIT)
            if len(conversation_text) > max_chars:
                conversation_text = conversation_text[:max_chars]
            
            # Create input prompt for Gemini
            input_prompt = f"[Post ID: {post_id}] {conversation_text}"
            
            try:
                # Get Gemini API response
                response = gemini_generate_structured(
                    client=gemini_client,
                    input_prompt=input_prompt,
                    system_instruction=system_instruction,
                    response_schema=response_schema,
                    max_output_tokens=500  # Increased for detailed reasoning
                )
                
                # Parse response
                response_data = json.loads(response.text)
                
                # Update counters
                total_requests_sent += 1
                # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
                estimated_tokens = len(input_prompt) // 4 + len(response.text) // 4
                total_tokens_used += estimated_tokens
                
            except HttpError as e:
                # Log the error with detailed information
                error_message = f"HTTP Error {e.status_code}"
                error_details = f"Status: {e.status_code}, Reason: {e.reason}"
                log_gemini_error(
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
                        response = gemini_generate_structured(
                            client=gemini_client,
                            input_prompt=input_prompt,
                            system_instruction=system_instruction,
                            response_schema=response_schema,
                            max_output_tokens=context_size
                        )
                        response_data = json.loads(response.text)
                        total_requests_sent += 1
                        estimated_tokens = len(input_prompt) // 4 + len(response.text) // 4
                        total_tokens_used += estimated_tokens
                    except HttpError as retry_e:
                        # Log retry error
                        retry_error_message = f"HTTP Error on retry {retry_e.status_code}"
                        retry_error_details = f"Status: {retry_e.status_code}, Reason: {retry_e.reason}"
                        log_gemini_error(
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
            except JSONDecodeError as e:
                # Log any other unexpected errors
                error_message = f"JSONDecodeError: {type(e).__name__}."
                error_details = str(e)
                log_gemini_error(
                    logger, 
                    post_id, 
                    len(conversation_text), 
                    error_message, 
                    error_details
                )
                # response_data = [{'user_id': '[User ID]', 'post_id': '[Post ID]', 'comment_id': '[Comment ID]', 'is_antisemitic': False, 'reasoning': '[Reasoning]', 'suggested_prompt_modifications': '[Suggested Prompt Modifications]'}]
            except Exception as e:
                # Log any other unexpected errors
                error_message = f"Unexpected error: {type(e).__name__}"
                error_details = str(e)
                log_gemini_error(
                    logger, 
                    post_id, 
                    len(conversation_text), 
                    error_message, 
                    error_details
                )
                continue  # Skip this conversation and continue with next
            
            # Process response data
            if response_data and isinstance(response_data, list) and len(response_data) > 0:
                for assessment in response_data:
                    structured_output = response.text
                    # Add conversation-specific fields
                    assessment['gemini_id'] = str(uuid.uuid4())
                    assessment['sheet_name'] = 'conversations'
                    assessment['post_id'] = post_id
                    assessment['conversation_length'] = len(conversation_text)
                    assessment['tokens_used'] = -1 # TODO: add this
                    gemini_rows.append(assessment)
            
            # Update progress
            conversations_analyzed += 1
            progress_bar.update(1)
            progress_bar.set_postfix({'tokens': f"{total_tokens_used:,}", 'requests': f"{total_requests_sent:,}"})
            # Rate limiting
            time.sleep(1.1)
        
        # Upload batch to Google Sheets
        if gemini_rows:
            add_rows_to_sheet(
                google_sheets_service, spreadsheet_id, geminis_sheet_id,
                gemini_rows,
                [column.lower() for column in gemini_columns]
            )
        
        batch_index += 1
    
    progress_bar.close()
    print(f"\nProcessing complete!")
    print(f"Total conversations analyzed: {conversations_analyzed}")
    print(f"Total tokens used: {total_tokens_used:,}")
    print(f"Total requests sent: {total_requests_sent:,}")

if __name__ == '__main__':
    args = get_args()
    worker(
        conversations_path=args.conversations_path,
        batch_size=args.batch_size,
        start_row=args.start_row,
        context_size=args.context_size
    )